# 意图路由与参数理解

## 目标

把用户的自然语言请求转换为稳定、可验证的业务意图和候选参数。路由不得因为用户换一种说法就改变业务含义；意图不明确时必须澄清，不能猜测执行。

## 当前实现与剩余问题

- 主聊天入口已调用 `interpret_turn()`，通过现有 OpenAI 兼容模型进行单轮结构化分类和槽位抽取。
- 输出由 Pydantic 枚举和字段约束校验；模型超时、输出无效或请求失败时返回 `UNCLEAR`，不会继续派发工具或预约流程。
- 结构化模型调用前有窄范围的确定性控制：待确认预约的明确拒绝会消费草稿并清理 checkpoint；无上下文的纯时间片段、无对象的“取消吗？”和明确的否定预约指令不会进入工具路由。
- `multi_intent` 不再默认作为终止澄清：路由器输出有序 `IntentPlan`，编排层分析步骤依赖。当前已支持“先查询本人预约，再选择并取消”的顺序计划；查询结果会保存为短期状态，后续选择只允许命中本次查询候选，取消仍需独立确认 token。
- 分类结果包含 speech act、歧义标记和槽位；创建/取消若同时被标成否定、拒绝或假设语气，会进入澄清，不会进入工具图。
- 活动预约工作流只作为摘要上下文传给分类器；预约解析图要求明确的创建/续接意图，且读取抽取槽位后仍由服务端解析资源、日期和时间。
- 普通问答不开放业务工具；通用工具图也不包含创建/取消预约的准备工具，防止后续模型自行改道。
- 指定日期/时段的可用性意图已经单独识别；因当前没有对应的实时区间查询工具，会明确说明能力边界，不会编造可用性。
- `route_request()` 暂时保留为旧测试和内部兼容用的确定性辅助函数；生产聊天入口不再用它作为主分类器。
- 尚未建立完整的人工标注改写语料、离线指标和 shadow 对比；这些工作完成前，不能据此宣称达到目标准确率。

典型误判：

| 用户表达 | 应识别 | 现有规则容易导致 |
|---|---|---|
| 预约规则是什么 | `POLICY_QA` | `BOOKING_CREATE` |
| 预约如何取消 | 规则问答或澄清 | `BOOKING_CANCEL` |
| 我不想取消预约 | 否定/一般对话 | `BOOKING_CANCEL` |
| 下周五下午有哪些实验室可以预约 | `AVAILABILITY_QUERY` | 仅列资源或落入普通对话 |

## 目标意图集合

第一阶段使用显式枚举，避免把“预约”统称为一个意图：

- `POLICY_QA`：预约规则、流程、材料等知识问答。
- `RESOURCE_SEARCH`：查询实验室或设备目录，不含特定时段可用性要求。
- `AVAILABILITY_QUERY`：查询给定日期/时段的实时可用资源。
- `MY_BOOKINGS_QUERY`：查询当前登录用户自己的预约。
- `ADMIN_PENDING_QUERY`：管理员查询其他用户的待审批预约。
- `BOOKING_CREATE`：明确请求创建预约。
- `BOOKING_CANCEL`：明确请求取消预约。
- `BOOKING_CONTINUE`：补充当前未完成预约草稿。
- `MULTI_INTENT`：一句话中存在多个独立请求。
- `GENERAL`：业务范围外的普通问答。
- `UNCLEAR`：无法安全确定用户意图。

## 识别契约

新增一个集中式 `interpret_turn()` 服务，输入只包含必要上下文：

```text
current_user_message
current_business_time
business_timezone
active_workflow_summary: type + phase + missing_fields | null
```

输出使用严格的 Pydantic schema，建议字段如下：

```json
{
  "intent": "AVAILABILITY_QUERY",
  "speech_act": "query",
  "slots": {
    "laboratory_text": null,
    "equipment_text": null,
    "date_text": "下周五",
    "time_text": "下午",
    "booking_status": null,
    "booking_id_text": null,
    "query_scope": null
  },
  "mentioned_fields": ["date_text", "time_text"],
  "missing_fields": ["specific_time_slot"],
  "ambiguous": false,
  "clarification_question": "你想查询下午哪个预约时段？"
}
```

契约要求：

- `intent`、`speech_act` 只能取 schema 定义值；额外字段拒绝，而不是静默接收。
- `speech_act` 区分 `query`、`request_action`、`confirmation`、`rejection`、`negated`、`hypothetical`。
- 模型只提取名称文本、日期表达、时间表达和用户明确提供的预约编号原文；预约编号仍需服务端验证，实验室 ID、设备 ID、用户 ID、角色和权限由服务端产生。
- 不要求模型返回思维链；如需调试，只记录意图、槽位、路由版本和简短分类原因码。
- 模型无法确定时输出 `UNCLEAR` 或 `MULTI_INTENT`，由服务端选择澄清或顺序执行。

## 处理流程

1. 规范化空白、全角/半角标点、大小写和常见语音转写噪声，但保留原始消息用于审计策略。
2. 读取本轮消息和最少量结构化工作流状态；不要将整段对话摘要当作当前意图。
3. 调用结构化意图/参数识别器。规则只处理确定性控制信号，例如待确认状态下的明确确认/拒绝；多个请求需要输出步骤计划和依赖关系。
4. 服务端解析实体候选、转换日期时间，并基于业务时区校验；同名或模糊实体必须让用户选择。
5. 对 `POLICY_QA`、目录查询、可用性查询、预约创建和取消映射到不同应用服务；`multi_intent` 进入计划编排器，不直接进入通用模型。
6. 对有依赖的计划按步骤执行：只读步骤先完成，写步骤等待目标选择和用户确认；每一步都重新做权限、归属和实时状态校验。
7. 创建/取消只能生成预览，经过用户确认后再次校验并执行；授权永远取自认证上下文。
8. 意图、计划版本、步骤状态、识别器版本、结构化参数、澄清结果、工具结果写入脱敏的运行审计字段。

## 工作流续接规则

- `workflow_active` 只能作为分类上下文，不能直接强制设置 `BOOKING_CONTINUE`。
- 用户只补充缺失字段时，识别器需返回 `BOOKING_CONTINUE` 和本轮明确提到的字段。
- 用户提出新的业务问题时，先处理新意图；原预约草稿保持待续接，不因新消息自动修改。
- 预约流程不活跃时，`BOOKING_CONTINUE` 返回明确的“没有待续接预约”结果，不进入通用模型猜测。
- 目前项目如不支持“修改已提交预约”，不得将其误映射到创建草稿；应澄清或拒答该动作。

## 实施步骤

- [x] 建立意图枚举和 Pydantic 输出 schema。
- [ ] 从 `AI_BAD_CASES.md`、现有测试和实际误判中整理标注语料。
- [ ] 每类意图准备多种自然改写，并添加否定、规则询问、引用、错别字、复合句和多轮续接反例。
- [x] 实现结构化识别器，并保留服务端确定性日期/时段和实体验证。
- [x] 将生产聊天入口切换到 `interpret_turn()`，移除预约解析器中的意图猜测和活动状态强制分支。
- [x] 建立有序多意图计划契约，并落地“查询预约 -> 选择预约 -> 取消确认”顺序编排。
- [ ] 先以 shadow mode 记录新旧路由差异，再切换业务流量。
- [ ] 扩展独立多意图、并行只读多意图和更多依赖计划的执行器。

## 验收门槛

- 离线语料按意图统计 precision、recall、macro-F1 和混淆矩阵；建议首轮 macro-F1 不低于 0.95，再依据真实风险调整。
- 创建、取消的否定句、问规则和假设句在固定对抗集上不得触发写操作。
- 低信息或歧义输入必须澄清；不得把任意非空输入自动转成预约创建。
- 日期、时间和实体必须经服务端领域校验；模型输出不能覆盖用户身份、权限或资源归属。
- 每个已修复误判都成为版本控制中的回归样例。

## 现有代码映射

- 主要替换：`backend/app/services/agent_router.py`。
- 保留并收敛领域解析：`backend/app/services/booking_workflow.py`、`backend/app/domain/booking/resolver.py`、`backend/app/domain/booking/query.py`。
- 主调用位置：`backend/app/services/ai_services.py` 的 `chat_llm()`。
- 测试应纳入仓库，不能继续被 `.gitignore` 排除。

