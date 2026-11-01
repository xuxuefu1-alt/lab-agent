# 智能实验室预约 Agent

这是一个可本地运行、可容器化部署、支持持续更新的实验室预约 Agent 项目，包含 Vue 前端、FastAPI 后端、意图识别、多意图计划编排、工具调用、RAG、会话记忆和可观测性。

## 快速体验

### 方式一：本地开发（推荐）

后端默认使用 SQLite，Redis 可选；没有模型密钥时，健康检查和普通业务接口仍可启动，调用 AI 时会返回明确的配置提示。

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:mysql_url = "sqlite:///./lab_agent.db"
$env:REDIS_URL = "redis://:lag-dev-redis@127.0.0.1:6379/0"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

另开终端启动前端：

```powershell
cd fronted
npm ci
npm run dev
```

访问 `http://localhost:5173`，后端文档访问 `http://localhost:8000/docs`。

### 方式二：Docker Compose Demo

该模式会启动 MySQL、Redis、后端和 Nginx 前端：

```powershell
$env:LLM_API_KEY = "你的模型密钥"
docker compose -f docker-compose.demo.yml up --build
```

访问 `http://localhost:8080`，停止服务：

```powershell
docker compose -f docker-compose.demo.yml down
```

## 生产级链路

```text
用户输入
  -> 会话与上下文加载
  -> 意图识别与置信度判断
  -> 多意图拆分与计划编排
  -> 权限校验与工具调用
  -> 数据库事务 / Redis Checkpoint
  -> 结构化结果与 SSE 流式响应
  -> 审计日志、指标、链路追踪
```

核心目录：

- `backend/app/services/agent_router.py`：意图识别与路由
- `backend/app/services/agent_plan_orchestrator.py`：多意图计划编排
- `backend/app/services/ai_services.py`：Agent 主流程、工具调用和响应生成
- `backend/app/services/ai_memory_service.py`：会话记忆、摘要和工作流状态
- `backend/app/services/ai_checkpoint.py`：LangGraph Checkpoint
- `backend/app/services/ai_tools.py`：业务工具
- `backend/data/kb`：RAG 知识库
- `ops/observability`：Prometheus、Grafana、Loki、Tempo

## 测试与质量门禁

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\fronted
npm run build
cd ..
docker compose -f docker-compose.demo.yml config
```

GitHub Actions 会在 `master`、`main`、`develop` 分支执行后端测试和前端构建。

## Render 在线体验

仓库根目录提供 `render.yaml`，导入 GitHub 仓库后可创建后端 Web Service 和前端 Static Site。Demo 后端默认使用 SQLite 和内存 Checkpoint，不要求额外购买数据库或 Redis；只需在 Render Secret 中配置 `LLM_API_KEY`，并将前端 `VITE_API_BASE_URL` 指向后端域名加 `/api`。

详细步骤见 [`docs/开源部署与在线体验指南.md`](docs/开源部署与在线体验指南.md)。

## 安全要求

- 不提交 `.env`、模型密钥、JWT 密钥、数据库密码和真实业务数据。
- 生产环境必须替换 JWT 密钥，并使用外部 MySQL/PostgreSQL 与 Redis Stack。
- Demo 数据与生产数据隔离，Render 免费实例可能休眠。
