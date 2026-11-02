# 智能实验室预约 Agent

这是一个可本地运行、可容器化部署、支持持续更新的实验室预约 Agent 项目，包含 Vue 前端、FastAPI 后端、意图识别、多意图计划编排、工具调用、RAG、会话记忆和可观测性。

## 快速体验

### 方式一：本地开发（推荐）

本地和在线环境都以 MySQL 为业务数据库。自动化测试可显式使用 SQLite 隔离测试数据；生产模式会拒绝 SQLite，并要求外部 MySQL 与 Redis Stack。

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:mysql_url = "mysql+pymysql://lab_agent:lab_agent_demo@127.0.0.1:3306/lab_agent"
$env:REDIS_URL = "redis://:lag-dev-redis@127.0.0.1:6379/0"
docker compose -f ..\docker-compose.demo.yml up -d mysql redis
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

仓库根目录提供 Render 免费基础设施 Blueprint。云端业务数据使用 MySQL 兼容托管库，Checkpoint 使用 Redis Cloud，RAG 使用 Qdrant Cloud，聊天使用项目现有的 DeepSeek API 配置。DeepSeek 模型调用按官方价格计费；免费托管不等于模型调用免费。需要配置 `mysql_url`、`REDIS_URL`、`QDRANT_URL`、`QDRANT_API_KEY`、`LLM_API_KEY`、`CORS_ORIGINS` 和前端 `VITE_API_BASE_URL`。免费服务会休眠或有资源配额，不提供生产 SLA；不要把本机 `127.0.0.1` 地址填入云端配置。

详细步骤见 [`docs/开源部署与在线体验指南.md`](docs/开源部署与在线体验指南.md)。

## 安全要求

- 不提交 `.env`、模型密钥、JWT 密钥、数据库密码和真实业务数据。
- 公开体验只使用合成数据；不要向模型 API 发送隐私或敏感业务数据。
- 免费托管适合功能体验和作品展示，不提供生产 SLA，也不保证服务永不休眠。
