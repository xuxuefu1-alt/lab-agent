# 本地观测环境

## 启动

```powershell
cd ops/observability
Copy-Item .env.example .env
# 编辑 .env，至少替换 Redis 和 Grafana 密码
docker compose up -d
docker compose ps
```

## 管理界面

- RedisInsight: http://localhost:5540
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Loki: http://localhost:3100/ready
- Tempo: http://localhost:3200/ready

Grafana 已预置 Prometheus、Loki、Tempo 三个数据源。默认账号来自 `ops/observability/.env`，不要使用示例密码部署到共享环境。

## 后端配置

在 `backend/.env` 增加以下配置，并使用与 Compose 一致的 Redis 密码：

```ini
APP_ENV=development
REDIS_URL=redis://:change-this-redis-password@127.0.0.1:6379/0
AI_CHECKPOINT_PREFIX=lab_agent_checkpoint
AI_CHECKPOINT_TTL_MINUTES=1440
OTEL_SERVICE_NAME=lab-agent-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4320
```

LangGraph checkpoint 使用 Redis Stack 的 RediSearch 索引；生产环境不能将 `REDIS_URL` 指向普通 Redis 镜像。
生产部署请设置 `APP_ENV=production`，并使用独立的 Redis 密码、持久化卷和受控的 checkpoint 前缀。

然后启动后端：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

指标地址为 `http://localhost:8000/metrics/`。Prometheus 已配置抓取该地址，Trace 通过 OTel Collector 转发到 Tempo。
后端结构化 JSON 日志会同时写入标准输出和 OTel Collector，再由 Loki 保存；每个 API 响应会带 `X-Request-ID`，同一请求的日志会包含 request ID 和可用的 trace/span ID。指标按 FastAPI 路由模板聚合，不使用原始 URL 参数作为标签。
Agent Trace 覆盖意图分类、预约工作流、对话图和工具调用；`lab_agent_tool_calls_total` 可按工具名和成功/失败结果观察工具调用情况。

Prometheus 已加载 `prometheus/alerts.yml`，包含后端抓取中断、5xx 比例升高和 p95 延迟升高规则，并将告警分组发送到 Alertmanager。当前接收器只保留本地状态，不会向外部发送通知；配置真实接收器前需确定通知渠道并通过环境密钥管理凭证。

## 观测链路验收

在 Grafana Explore 中可分别用以下方式检查日志和 Trace：

```logql
{service_name="lab-agent-backend"} | request_id="替换为实际的 X-Request-ID"
```

`request_id` 是日志结构化元数据，不是 Loki 流标签；先用 `service_name` 选择流，再用 `| request_id="..."` 过滤。日志查询需要范围查询，直接调用 Loki instant query 接口 `/loki/api/v1/query` 会返回 400；使用 Grafana Explore 或 `/loki/api/v1/query_range`。

Tempo 可在 Grafana Explore 按 `service.name` 搜索，也可检查单条 Trace：

```powershell
Invoke-RestMethod http://localhost:3200/api/traces/<trace-id>
```

Prometheus 的 `/api/v1/alertmanagers` 应显示 `http://alertmanager:9093/api/v2/alerts` 且 `droppedAlertmanagers` 为空；Alertmanager 健康检查地址为 `http://localhost:9093/-/healthy`。

2026-10-31 本地验收已确认：Loki 保存了 smoke 请求的 3 条日志，并可通过 `request_id=otel-e2e-20261031` 检索；Tempo 可搜索到对应 Trace `3e41bf8629885a7e6a2ba5c8573ee2ed`；Prometheus 已发现 Alertmanager 且没有 dropped 实例；Alertmanager API 接收了临时合成告警，并在 `endsAt` 到期后从活动告警中清除。三条 Prometheus 规则均已加载且当前为 inactive。该合成告警验证的是 Alertmanager 接收与过期流程，不代表外部通知已送达；当前配置没有外发接收器。

规则文件和阈值回归测试可在项目根目录运行：

```powershell
docker run --rm --entrypoint=promtool -v "${PWD}/ops/observability/prometheus:/etc/prometheus:ro" prom/prometheus:v3.5.0 check rules /etc/prometheus/alerts.yml
docker run --rm --entrypoint=promtool -v "${PWD}/ops/observability/prometheus:/etc/prometheus:ro" prom/prometheus:v3.5.0 test rules /etc/prometheus/alerts_test.yml
```

测试覆盖后端抓取中断、5xx 比例和 p95 延迟告警，并检查 `for` 持续时间未满足时不会提前触发。CI 的 `observability` job 使用相同 Prometheus 版本执行这两项校验。

## 回归门禁

GitHub Actions 的 `Quality gates` 工作流会运行后端 unittest、Agent 质量评测、前端生产构建、Prometheus 告警规则校验和 `git diff --check`。CI 使用 SQLite 和虚拟模型配置，不会调用真实模型、MySQL 或 Redis；依赖真实 Redis Stack/模型的联调仍需在隔离环境单独执行。

本地运行同一组后端测试：

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s quality -p "test_*.py" -v
```

## 日常排查

```powershell
docker compose ps
docker compose logs --tail 200 lag-otel-collector
docker logs --tail 200 lag-redis
docker compose down
```

停止容器不会删除 named volumes；如需清空本地观测数据，必须显式执行：

```powershell
docker compose down -v
```
