# 实验室管理 Agent 生产级架构

## 目标

本系统定位为“实验室预约业务 Copilot”，不是开放式聊天机器人。Agent 只负责理解请求、补齐参数、调用受控工具和解释真实结果；权限、业务规则、数据一致性和写入确认都由服务端代码负责。

## 请求处理链路

```text
HTTP / SSE
  -> 认证与用户上下文
  -> 会话加载（数据库消息 + 摘要）
  -> 预约工作流状态加载（Redis checkpoint + 数据库兜底）
  -> 确定性 Agent Router
  -> 业务子图 / 只读 Tool / 普通问答图
  -> 服务端权限与业务规则校验
  -> 结构化 blocks + 简短正文
  -> 消息、审计、工作流状态持久化
```

## 路由边界

`app/services/agent_router.py` 是业务意图的唯一入口，当前路由优先级如下：

1. 取消预约
2. 查询预约
3. 查询实验室与设备
4. 继续已有预约流程
5. 创建预约
6. 普通问答

同一个请求只允许进入一个业务入口。预约查询不能落入创建预约，资源查询不能因为包含“预约”二字而进入写流程。

管理员待审批查询使用统一过滤契约，不为每个时间说法创建独立意图：

```text
intent = ADMIN_BOOKING_QUERY
status = 待审核
time_from = 可选标准时间边界
time_to = 可选标准时间边界
```

“今天”“最近一个月”“本月”“本周”和指定日期由预约查询过滤器解析，工具只执行结构化过滤参数。

## 预约工作流

预约使用 LangGraph 子图和 Redis Stack checkpointer 保存可恢复状态，数据库保存可审计的结构化工作流状态：

```text
collecting_requirements
  -> slot_validation_failed（非法时段或资源冲突）
  -> pending_confirmation
  -> executing（由服务端确认接口执行）
  -> completed / failed / expired / reset
```

实验室和设备解析采用确定性领域解析器：完整名称优先、名称 stem 次之、唯一位置匹配再次之、最后才使用保守模糊匹配。多个候选不会猜测，必须让用户选择。

## Tool 安全边界

- Tool 输入使用 Pydantic schema 约束。
- 当前用户、角色、资源归属由认证上下文提供，不能由模型或用户消息覆盖。
- 普通用户只能查看和操作自己的预约。
- 管理类工具必须在服务端做管理员校验，Prompt 不具备授权能力。
- 创建、取消等写操作必须先生成确认 token，再由明确确认消息触发。
- 写操作使用 Redis 幂等锁和数据库事务，避免重复提交。
- 工具、知识库、会话摘要均视为不可信数据，不能升级为系统指令。

## 上下文与 checkpoint

- 前端只提交本轮新消息，服务端从会话表加载历史。
- 普通聊天使用“摘要 + 最近消息”，避免每次发送完整 20 条历史。
- 预约 checkpoint 独立于普通聊天 checkpoint，摘要压缩不会破坏预约草稿。
- checkpoint 中的历史工具结果只用于模型理解，不得再次渲染到当前回复。
- reset/delete 会同时处理数据库会话、工作流状态和 chat/booking checkpoint。

## 输出契约

返回对象由两部分组成：

- `content`：面向用户的一句或几句简短说明。
- `blocks`：实验室、设备、预约确认、取消确认等结构化卡片数据。

卡片负责详细展示，正文不重复表格、不展示“生成卡片”“工作流”等内部实现术语。

## 可观测性与发布门禁

每次请求至少要能关联：用户、会话、意图、工具调用、结果状态和异常日志。生产环境必须使用 Redis Stack checkpointer，启动时检查依赖；数据库、Redis、模型和知识库故障都要有明确降级结果。

发布前必须通过：

- 预约多轮续接、继续、确认、取消和冲突场景；
- 查询与创建意图隔离；
- 完整实验室名称优先和位置简称解析；
- 普通用户越权、伪造管理员、跨用户预约操作；
- prompt injection、工具失败、checkpoint 过期和 Redis 不可用；
- 后端单测、安全测试、前端构建和关键浏览器链路。

## 当前代码边界

- `app/services/agent_router.py`：请求路由。
- `app/domain/booking/resolver.py`：实验室实体解析。
- `app/services/booking_graph.py`：预约子图。
- `app/services/booking_workflow.py`：日期、时段、设备和草稿解析。
- `app/services/ai_tools.py`：强类型工具与服务端权限校验。
- `app/services/ai_memory_service.py`：会话、摘要、工作流元数据和审计。
- `app/services/ai_checkpoint.py`：LangGraph checkpoint 生命周期。

后续新增能力应进入对应边界，禁止继续把业务判断堆到 `ai_services.py` 的单一函数中。
