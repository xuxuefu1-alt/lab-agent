# 实验室预约 Agent 企业级落地评估与实施方案

**评估对象**：`lag-agent` 当前版本  
**评估日期**：2026-10-15  
**评估定位**：面向实验室预约场景的企业级 Agent 演进方案  
**结论先行**：当前项目已经完成“认证用户调用 LLM + 基础知识库检索”的最小闭环，但本质上仍是一个带 RAG 的聊天接口，不是能够安全执行预约业务的企业级 Agent。

## 1. 当前能力盘点

当前项目已经具备：

| 能力 | 当前实现 | 评价 |
|---|---|---|
| 用户认证 | JWT 登录、注册、当前用户校验 | 有基础能力，但权限模型不完整 |
| 对话入口 | `POST /api/ai/chat` | 能接收多轮消息并返回文本 |
| 知识检索 | Chroma + `BAAI/bge-small-zh-v1.5` | 能做最小 RAG |
| 知识来源 | `backend/data/kb/*.md` | 适合原型，不适合生产知识治理 |
| 前端交互 | Vue 对话页、快捷提问、复制回复 | 有交互外壳，但会话主要保存在前端内存 |
| 文件上传 | `/api/files/upload` | 只完成文件落盘，没有接入解析、切片、审核、索引 |
| 业务系统 | 暂无实验室、设备、预约、审批等真实业务模型与 API | Agent 无法执行真实业务动作 |

当前 Agent 的核心链路可以概括为：

```text
用户消息
  -> 前端携带完整 history
  -> 后端取最后一条 user 消息
  -> Chroma 检索最多 2 个文档
  -> 将原文拼入 system prompt
  -> 调用 chat completion
  -> 返回一段文本
```

代码依据：

- 对话入口仅调用 `ai_services.chat_llm`：`backend/app/api/ai.py:12-15`
- Agent 逻辑集中在单个服务函数：`backend/app/services/ai_services.py:19-54`
- 检索以整个 Markdown 文件为粒度：`backend/app/services/kb_services.py:32-45`
- 文件上传未要求登录，且没有触发知识库处理：`backend/app/api/upload.py:14-49`

## 2. 与企业级 Agent 的核心差距

### 2.1 P0：必须优先解决的落地阻断项

| 优先级 | 不足 | 当前表现 | 风险 | 方案 |
|---|---|---|---|---|
| P0 | 没有真实业务工具 | Agent 只能回答，不能查询实验室、检查时间冲突、创建预约、取消预约、提交审批 | 用户得到“看起来正确”的建议，但系统状态不会变化 | 建立显式 Tool 层，所有业务动作通过后端 API/Service 执行，禁止让模型直接操作数据库 |
| P0 | 没有状态机 | 没有“收集预约参数 -> 校验 -> 用户确认 -> 执行 -> 返回结果”的流程 | 多轮对话容易丢参数、误执行、无法恢复 | 使用显式 Workflow/State Machine，预约流程至少包含 `collecting`、`validated`、`awaiting_confirmation`、`executing`、`completed`、`failed` |
| P0 | 权限边界未闭合 | `/api/files/upload` 没有 `get_current_user`；角色字段存在但没有权限依赖 | 任意可访问接口的人都可能上传文件；学生、审批人、管理员没有真实权限隔离 | 上传、知识库发布、预约审批、管理查询分别增加 RBAC/ABAC 检查 |
| P0 | 关键业务数据不存在 | 数据库只有 User 模型；知识库内容描述了预约规则，但没有 `lab`、`equipment`、`booking`、`approval` 等表 | Agent 无法保证实时性和一致性，无法支撑企业业务闭环 | 先完成业务域模型和事务 API，再接入 Agent Tool |
| P0 | 不可审计 | 只返回最终文本，没有 request id、trace、工具调用、输入输出摘要、操作者和结果 | 出错后无法回答“谁在什么时间让 Agent 做了什么” | 建立 Agent Run、Tool Call、Audit Event 三类记录，敏感字段脱敏 |
| P0 | 没有评测门禁 | 仓库没有 Agent 测试集、回归评测、工具调用正确率指标 | Prompt 或模型变更可能悄悄破坏业务 | 建立固定评测集，发布前必须通过事实性、拒答、工具参数、权限和故障恢复测试 |

### 2.2 P1：影响可靠性和可运营性的缺口

| 不足 | 当前表现 | 企业级改造方向 |
|---|---|---|
| 会话不持久化 | 前端 `conversations` 和 `messages` 是本地内存，刷新后丢失；切换历史仅展示硬编码内容 | 后端持久化 Conversation、Message、Summary，并支持分页、归档、删除 |
| 客户端可伪造历史 | 后端信任客户端传入的 `assistant` 消息，并将其作为模型上下文 | 服务端保存消息；客户端只提交新 user message；历史从数据库读取 |
| 输入边界不足 | `ChatMessage` 没有长度、条数、总 token 或内容类型限制 | 增加请求大小限制、单轮长度限制、历史截断/摘要、超时和取消机制 |
| RAG 文档粒度过粗 | 每个 Markdown 文件作为一个向量，检索后只保留最多两个文件 | 按标题/段落切片，保存 `doc_id/version/chunk_id/title/effective_at/owner`，支持过滤和引用 |
| 没有知识版本与发布流程 | Chroma 只在 collection 为空时初始化；后续新增 Markdown 不会自动入库 | 文档入库任务、版本、审核、发布、回滚、失效时间和索引状态独立管理 |
| 没有引用和证据 | 模型只看到拼接文本，前端没有展示来源、段落或置信度 | 返回 `citations`，展示来源文档、章节和命中片段；无证据时明确说不知道 |
| 检索分数不可靠 | 使用 `1 / (1 + distance)` 并以 `0.5` 作为固定阈值，没有验证距离定义和场景效果 | 通过离线数据标定阈值；必要时增加 rerank、关键词检索和结构化过滤 |
| 工具失败策略缺失 | LLM 调用异常统一转成泛化错误；无超时、重试、熔断、降级 | 对模型、向量库、业务 API 分别定义 timeout/retry/backoff/fallback |
| 无流式响应 | 后端等待完整结果后返回 | 使用 SSE/WebSocket 返回 token、工具状态和最终结果，避免长请求无反馈 |
| 错误语义不规范 | 业务异常 HTTP status 仍为 200；异常信息存在编码混乱和过度泛化 | 使用标准 HTTP 状态码、稳定错误码、request id；服务端记录原始异常 |
| 配置和资源管理不足 | LLM、Embedding、数据库连接池、超时等缺乏结构化配置 | 所有运行参数环境化，启动时校验，区分开发/测试/生产配置 |

### 2.3 P2：影响规模化和用户体验的缺口

- 没有管理员知识库管理页：无法查看文档状态、重新索引、撤回、查看失败原因。
- 没有业务角色工作台：审批人无法从 Agent 中查看待审批任务并完成审批。
- 没有人工接管：高风险、低置信度、规则冲突或工具失败时无法转人工。
- 没有多租户/数据域设计：后续接入不同学院、实验室或组织时会出现数据串读风险。
- 没有成本治理：未记录 token、模型费用、调用次数和按用户/功能的预算。
- 没有容量和稳定性策略：Embedding 模型在进程内初始化，Chroma 使用本地持久化文件，不适合多实例水平扩展。
- 前端存在 mock 对话和硬编码历史；“重新生成”、附件、语音按钮是展示状态，尚未形成真实能力。

## 3. 目标产品形态

建议将产品定位从“AI 聊天助手”升级为：

> **实验室预约业务 Copilot：负责理解用户意图、补齐参数、调用受控业务工具、解释结果，并在不确定或高风险时请求确认或转人工。**

Agent 应该只负责四类事情：

1. **理解**：识别用户意图和实体，例如实验室、日期、时间段、设备、用途。
2. **检索**：从受控知识库和实时业务 API 获取依据。
3. **编排**：按照预约工作流决定下一步动作。
4. **解释**：用用户能理解的语言返回结果、引用和下一步。

Agent 不应该负责：

- 直接修改数据库；
- 仅凭语言模型判断时间是否可预约；
- 仅凭 Prompt 决定用户是否有权限；
- 在没有用户确认的情况下执行预约、取消、审批等不可逆动作；
- 把检索文档中的指令当作系统指令执行。

## 4. 推荐目标架构

```text
Vue Web
  |
  | HTTPS / SSE
  v
API Gateway
  |
  +-- AuthN/AuthZ ---- User / Role / Permission
  |
  +-- Conversation API ---- Conversation / Message / Run
  |
  +-- Agent Orchestrator
  |      |
  |      +-- Intent & Entity Extraction
  |      +-- Workflow State Machine
  |      +-- Policy / Confirmation Gate
  |      +-- Model Gateway
  |      +-- Tool Registry
  |             |
  |             +-- search_laboratories
  |             +-- check_availability
  |             +-- create_booking
  |             +-- cancel_booking
  |             +-- list_my_bookings
  |             +-- submit_equipment_issue
  |
  +-- Knowledge Service
  |      +-- Upload -> Parse -> Chunk -> Embed -> Review -> Publish
  |      +-- Vector Store + Metadata Filter + Citation
  |
  +-- Business Services
  |      +-- Laboratory
  |      +-- Equipment
  |      +-- Booking
  |      +-- Approval
  |
  +-- Observability
         +-- Structured Log
         +-- Trace
         +-- Metrics
         +-- Evaluation
```

### 4.1 Agent 编排建议

当前场景不建议使用完全自由的自主循环，建议采用“显式工作流 + 有限工具调用”：

```text
接收消息
  -> 意图分类
  -> 提取结构化参数
  -> 参数校验
  -> 查询/执行工具
  -> 需要写操作时请求用户确认
  -> 执行并记录审计
  -> 返回结果和引用
```

可支持的第一批意图：

| 意图 | 是否允许写操作 | 最小工具链 |
|---|---:|---|
| 查询实验室 | 否 | `search_laboratories` |
| 查询设备 | 否 | `search_equipment` |
| 查询空闲时段 | 否 | `check_availability` |
| 查询我的预约 | 否 | `list_my_bookings` |
| 创建预约 | 是 | `check_availability` -> 用户确认 -> `create_booking` |
| 取消预约 | 是 | `get_booking` -> 用户确认 -> `cancel_booking` |
| 预约规则问答 | 否 | `retrieve_policy` |
| 设备故障上报 | 是 | `create_equipment_issue` -> 用户确认 |
| 无关问题 | 否 | 受控拒答 |

## 5. Tool 设计原则与示例契约

每个 Tool 必须具备：强类型输入、服务端权限校验、超时、幂等键、结构化输出、错误码和审计记录。

### `check_availability`

```json
{
  "name": "check_availability",
  "input": {
    "lab_id": 101,
    "date": "2026-10-20",
    "slot_no": 2
  },
  "output": {
    "available": true,
    "lab_id": 101,
    "date": "2026-10-20",
    "slot_no": 2,
    "conflicts": [],
    "rule_warnings": []
  }
}
```

### `create_booking`

```json
{
  "name": "create_booking",
  "input": {
    "lab_id": 101,
    "date": "2026-10-20",
    "slot_no": 2,
    "purpose": "材料测试"
  },
  "context": {
    "user_id": 123,
    "idempotency_key": "client-generated-uuid"
  }
}
```

执行约束：

- `user_id` 必须从认证上下文获取，不能由模型传入；
- 服务端重新检查账号状态、冻结状态、每周次数和时间冲突；
- 写操作必须有用户确认；
- 使用数据库事务和唯一约束防止并发重复预约；
- 重试时使用幂等键，避免重复创建；
- 返回业务结果，不让模型自行推断“是否成功”。

## 6. 知识库升级方案

### 6.1 数据处理链路

```text
上传
  -> 文件类型和大小校验
  -> 病毒/恶意文件扫描
  -> 文本解析
  -> 标题/段落切片
  -> 清洗和去重
  -> 生成 Embedding
  -> 质量检查
  -> 人工审核
  -> 发布到线上索引
```

### 6.2 建议元数据

```text
document_id
version
title
source_uri
content_hash
department
access_scope
status: draft/reviewing/published/archived
effective_at
expired_at
created_by
approved_by
updated_at
```

每个 chunk 至少保存：

```text
chunk_id
document_id
version
section_title
content
embedding_model
access_scope
```

### 6.3 生产检索要求

- 先按用户权限和有效时间过滤，再做向量检索；
- 保留文档标题、章节、版本和命中分数；
- 低于阈值时走“证据不足”分支，不强行生成答案；
- 对规则、时间、角色、状态等结构化信息优先查询业务 API；
- Agent 回答必须能返回引用；
- 知识文档与系统 Prompt、用户消息、工具结果分离，不能把外部文档中的指令当作高信任指令。

## 7. 安全与权限方案

### 7.1 立即整改

1. `/api/files/upload` 增加认证和管理员/知识库维护权限。
2. 所有写操作增加 RBAC 检查，不能只依赖 Prompt。
3. 注册接口限制角色为普通用户，管理员必须后台创建或由受控流程授予。
4. JWT 增加 `sub`、`iss`、`aud`、`iat`、`jti`，并支持撤销/轮换策略。
5. 登录增加失败次数限制、账号锁定、统一错误提示和审计日志。
6. 限制上传文件真实 MIME、压缩包内容、文件名、数量和总容量。
7. 不将原始用户内容、密钥、完整检索文档直接写入普通日志。
8. 外部检索内容、附件内容和工具返回文本全部视为不可信数据。

### 7.2 高风险动作确认矩阵

| 动作 | 默认权限 | 是否需要二次确认 | 是否审计 |
|---|---|---:|---:|
| 查询知识库 | 登录用户 | 否 | 是 |
| 查询空闲时段 | 登录用户 | 否 | 是 |
| 创建预约 | 登录用户且账号正常 | 是 | 是 |
| 取消预约 | 预约本人或管理员 | 是 | 是 |
| 审批预约 | 审批角色 | 是 | 是 |
| 上传/发布知识 | 知识库管理员 | 是 | 是 |
| 删除文档/批量变更 | 管理员 | 是，必要时人工复核 | 是 |

## 8. 可观测性与运营指标

每次 Agent Run 建议记录：

```text
request_id
trace_id
user_id
conversation_id
intent
model/provider
prompt_version
retrieval_query
retrieved_document_ids
tool_calls
tool_latency
model_latency
input_tokens
output_tokens
estimated_cost
final_status
error_code
human_handoff
```

建议首批指标：

| 指标 | 建议目标 |
|---|---:|
| API 成功率 | >= 99.5% |
| 工具参数校验通过率 | >= 99% |
| 预约冲突误判率 | 0 |
| 未经确认的写操作 | 0 |
| 有引用的知识回答占比 | >= 95% |
| 无证据问题的正确拒答率 | >= 95% |
| P95 查询响应时间 | <= 3 秒，流式首 token <= 1 秒 |
| Tool 调用可审计率 | 100% |
| 关键路径自动化回归通过率 | 100% |

## 9. 评测方案

不要只测试“回答是否通顺”，需要建立可重复的 Agent 评测集。

### 9.1 评测分类

| 类别 | 示例 |
|---|---|
| 正常问答 | 实验室开放时间、预约规则、安全规范 |
| 多轮补参 | “帮我预约明天下午” -> 追问实验室、用途、时间段 |
| 工具正确性 | 空闲查询、冲突检测、我的预约 |
| 写操作安全 | 没有确认时不能创建或取消 |
| 权限隔离 | 学生不能审批，普通用户不能发布知识 |
| 证据不足 | 知识库没有答案时明确拒答 |
| 冲突信息 | 两个版本规则不一致时提示冲突并转人工 |
| 恶意输入 | Prompt injection、伪造系统消息、恶意附件 |
| 工具异常 | 业务 API 超时、数据库不可用、重复提交 |
| 回归测试 | Prompt、模型、Embedding 变更前后对比 |

### 9.2 评测输出

每条样本至少保存：

```text
输入消息
用户角色
期望意图
期望工具及参数
是否需要确认
期望引用
期望最终状态
实际轨迹
评分
失败原因
```

发布门禁至少包括：

- 不允许的工具调用为 0；
- 未授权工具调用为 0；
- 预约写操作无确认为 0；
- 关键业务工具参数准确率达到 99%；
- 关键知识问题事实正确率达到 95%；
- 工具失败后能够返回明确降级结果；
- 评测失败时阻止 Prompt/模型版本发布。

## 10. 分阶段实施计划

### 阶段一：P0 基础收口

目标：把当前“可聊天原型”变成“可控的 Agent 服务”。

- 建立统一配置、日志、request id 和错误码；
- 将客户端 history 改为服务端 Conversation/Message；
- 增加消息长度、历史长度、超时和取消控制；
- 关闭未授权上传，补充角色权限；
- 拆分 `ai_services.py`：模型网关、检索服务、编排器、工具注册表；
- 建立 `AgentRun` 和 `ToolCall` 记录；
- 加入最小 pytest 测试和 20-50 条离线评测样本；
- 将知识库搜索结果改为结构化对象，不再拼成不可追踪的字符串。

**阶段验收**：所有请求有 trace；所有异常有稳定错误码；会话刷新不丢失；无权限用户不能上传或访问受限知识。

### 阶段二：P0 业务闭环

目标：让 Agent 能安全完成查询和预约。

- 建立实验室、设备、预约、审批、违规记录模型；
- 实现实验室查询、设备查询、空闲检查、我的预约等只读 Tool；
- 实现创建预约、取消预约，增加确认、幂等和事务；
- 业务规则放到领域服务，不放在 Prompt；
- 增加前后端统一的预约状态机；
- 前端展示工具进度、确认卡片、引用和失败原因。

**阶段验收**：查询结果来自实时业务 API；预约冲突在并发下仍然正确；所有写操作可回放、可审计。

### 阶段三：P1 知识工程化

目标：让知识库可维护、可回滚、可解释。

- 支持 PDF/DOCX/Markdown 解析；
- 文档切片、去重、版本、审核、发布和回滚；
- 增加关键词 + 向量 + rerank 的混合检索；
- 增加权限过滤、有效期过滤和引用；
- 建立知识库管理页和索引任务状态；
- 建立知识质量评测集。

**阶段验收**：每个知识回答能定位到文档和章节；文档更新有版本；索引失败可重试；无证据问题不会被强行回答。

### 阶段四：P1/P2 规模化运营

目标：满足多角色、多实例和持续运营要求。

- 使用独立向量数据库或托管向量服务，避免多实例共享本地 Chroma 文件；
- 引入 Redis/队列处理文档解析、Embedding 和异步任务；
- 增加模型路由、成本预算、限流、熔断和降级；
- 增加人工接管、反馈、标注和失败样本回流；
- 接入 OpenTelemetry、指标监控和告警；
- 建立 Prompt/模型/知识索引版本发布流程；
- 做负载、故障恢复、权限和安全测试。

**阶段验收**：服务可水平扩展；关键依赖故障时有降级；运营人员能定位一次请求的完整链路和成本。

## 11. 建议的代码演进边界

建议目录逐步演进为：

```text
backend/app/
  api/
    chat.py
    conversations.py
    knowledge.py
    bookings.py
  agent/
    orchestrator.py
    state.py
    policies.py
    model_gateway.py
    tool_registry.py
    tools/
      laboratory.py
      booking.py
      equipment.py
  knowledge/
    parser.py
    chunker.py
    indexer.py
    retriever.py
    citations.py
  domain/
    booking_service.py
    approval_service.py
  observability/
    tracing.py
    audit.py
    metrics.py
  models/
    user.py
    conversation.py
    booking.py
    knowledge.py
```

不要继续把所有行为堆积在 `backend/app/services/ai_services.py`。该文件目前同时承担历史整理、检索、Prompt 拼接、模型调用和异常转换，后续会难以测试和审计。

## 12. 最终判断

当前版本适合继续作为学习型原型，但距离企业级 Agent 至少还有三层能力差距：

1. **从回答到执行**：接入真实业务 Tool 和事务服务。
2. **从 Prompt 到控制**：用权限、状态机、确认和策略代码约束风险。
3. **从能运行到可运营**：补齐持久化、审计、观测、评测、成本和发布治理。

最合理的下一步不是继续堆 Prompt，而是先完成以下五件事：

1. 服务端持久化会话；
2. 建立实验室预约领域模型；
3. 实现只读查询 Tool；
4. 实现带确认和幂等的预约 Tool；
5. 建立第一版 Agent 评测集与审计链路。

完成这五件事后，项目才具备从“RAG 聊天演示”进入“可控业务 Copilot”的基础。
