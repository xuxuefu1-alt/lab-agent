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

指标地址为 `http://localhost:8000/metrics`。Prometheus 已配置抓取该地址，Trace 通过 OTel Collector 转发到 Tempo。

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
