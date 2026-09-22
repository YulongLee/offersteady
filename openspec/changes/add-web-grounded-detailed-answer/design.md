## Context

当前实时回答由 `ChatService` 先流式生成快答，再基于本地材料/向量检索生成详细回答；前端通过 `/api/v1/live-answer/questions/stream` 接收统一 SSE 事件。国内计费已有服务端商品目录、积分流水、会员权益和用量预留—结算能力。

阿里云百炼的 `deepseek-v4.1-flash` 具备 Responses API 的 `web_search` 工具能力，但当前代码只调用 Chat Completions，不传工具参数。联网能力需要限定在后端，且不能把国内积分语义带到 Global Commerce。

## Goals / Non-Goals

**Goals:**

- 为国内服实时面试增加会话级联网开关，默认关闭。
- 保持快答首字延迟链路不变，仅在详细回答阶段检索网页。
- 通过可替换的搜索网关返回结构化来源，并把来源显示给用户。
- 以 `web_answer` 作为独立计费类型，实现 20 点预留、成功结算、失败释放和 7 天以上会员免扣。
- 搜索失败时回退本地详细回答，不让联网故障阻断普通回答。

**Non-Goals:**

- 不修改桌面伴随程序，不在客户端保存搜索或模型密钥。
- 不为 Global 服引入国内积分；Global 需要后续单独设计联网额度。
- 不发送完整简历、音频、截图或全部历史给搜索服务。
- 不把搜索结果当作无条件事实；模型必须标注来源并避免无法核验的断言。

## Decisions

### 1. 采用后端搜索适配器，优先 Responses API

新增 `WebSearchGateway` 协议和阿里云百炼实现。适配器接收已脱敏的规范化问题和短上下文，返回标题、URL、摘要和抓取时间。默认使用 Responses API `tools=[{"type":"web_search"}]`；若生产地域或账号未开通，则配置开关关闭并走本地回退。

选择适配器而不是在前端直连，是因为密钥、超时、来源过滤、隐私和计费必须由服务端控制。搜索供应商替换不应改变 `ChatService` 的业务接口。

### 2. 搜索只作用于详细回答

流式回答先照常生成快答并立即发送。详细阶段在构建详细提示词前调用搜索网关；结果限制为最多 5 个来源、每个摘要最多 800 字符、总上下文最多 3,000 字符。搜索超时使用 2.5 秒上限，超时或空结果时不重试多次，直接使用本地检索上下文。

详细提示词使用明确的“联网资料”分区，要求区分来源事实、候选人材料和模型建议，并在答案末尾输出简洁来源列表。来源元数据写入任务的 `material_provenance.webSources`，不保存原始网页全文。搜索超时使用 20 秒上限，以覆盖百炼联网工具在高峰期约 4–12 秒的响应，同时仍限制最慢请求。

### 3. 计费沿用现有幂等预留模型

联网回答使用独立 `usage_kind=web_answer` 和 `webSearchAnswerPoints=20`。预留发生在创建任务前；只有可用的详细回答完成后结算，取消、异常、搜索失败后回退但模型也失败、超时均释放。重复的 `usageId` 返回同一预留结果。

国内会员仅当当前有效时间会员对应商品 `duration_days >= 7` 时免扣；1 天和 3 天会员仍按 20 点计费。积分不足返回可恢复的 409，不创建模型任务。

### 4. API 兼容与默认关闭

请求新增可选 `webSearchEnabled`，缺省或 `false` 等同现有链路。响应任务新增 `webSearchEnabled`、`webSearchStatus` 和 `webSources`，旧客户端忽略未知字段即可继续工作。自动回答也沿用会话开关，但只有用户明确打开后才联网。

### 5. 隐私和可观测性

搜索查询只使用规范化问题和经过长度限制的非敏感上下文，不上传原始材料。记录搜索耗时、结果数量、失败原因和计费来源，不记录问题正文或网页正文。前端明确展示“联网资料会发送给第三方搜索服务”的提示。

### 6. 开关切换缺陷修复

本轮用户批准修复联网关闭后普通快答失败。前端将正在处理的重复点击判定与计费请求编号分离：每次用户主动发起的请求使用包含模式和随机标识的新编号，不含问题正文；同一请求内保持编号不变。计费后端仍保留跨操作类型校验，不放松所有权校验或更改价格。

关闭联网时仅取消当前页面发起的未完成联网回答，保留已显示文字，立即恢复快答按钮；使用请求实例身份保护回调、渲染队列和 finally 清理，过滤已取消任务的迟到推送。通过现有取消接口通知服务器，不伪造前端退款。服务器在搜索返回后再次检查取消状态，流断开时收尾未完成任务并释放预留。已经发给供应商的同步搜索可能持续至返回或既有超时，但不得再写入答案或扣费。普通回答、截屏、模型配置和伴随程序不变。

本轮仅本地实现与自测，部署另行执行。

### 7. Explicit non-thinking web requests (2026-09-23)

The user approved disabling deep thinking for web-grounded detailed answers. Set `reasoning: {"effort": "none"}` in the DashScope Responses adapter only. Keep `tools=[{"type":"web_search"}]`, the configured model, output budget, timeout, fallback, and billing unchanged. Do not add an environment toggle or modify the ordinary Chat Completions gateway. This scoped change does not introduce streaming, retries, or a longer timeout and does not guarantee every search will finish within the existing deadline.

The provider documents `high` as the default for `deepseek-v4.1-flash`, and `none` as a supported explicit setting: [Responses API reasoning parameter](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses). Verification is local; deployment requires a separate request.

### 8. Independent simple-answer completion

Add a backward-compatible `quick_answer_completed` task flag (default false), expose it as `quickAnswerCompleted`, and emit `quick-completed` through the existing answer SSE and task-update channel after the quick stage and its continuation finish. Publish this before waiting for detailed retrieval/search. It is not a task terminal event or a billing settlement. Persisting the flag lets snapshot/realtime recovery retain the section state; existing stored tasks need no migration.

Map this optional flag to answer questions/tasks. Immediately flush first visible quick text and the stage boundary on the client; render completed simple text with final Markdown while detailed text remains loading. Keep whole-request action-button locking and cancellation unchanged to avoid concurrent duplicate requests/charges. The card names the active stage; a detail failure cannot turn the completed simple section back into a loading section. Older responses fall back to the existing detailed-section delimiter. Preserve cancelled-request identity guards.

This change does not alter prompts, models, retrieval/search order, provider timeout, or desktop software. It does not claim to fix provider first-token latency or proxy buffering. Add mocked slow-provider regressions and local desktop/mobile verification; no production deployment in this development task.

## Risks / Trade-offs

- [额外网络请求增加详细回答耗时] → 快答先流式显示；搜索限制 20 秒且只发生在详细阶段；失败快速回退本地上下文。
- [模型引用不准确] → 保存来源 URL、提示词要求引用、来源区域可展开，评测加入来源一致性案例。
- [搜索服务地域/权限不支持] → 启动时健康检查和配置开关；不可用时不显示可点击开关或明确提示并回退。
- [20 点与会员权益判断不一致] → 会员资格在服务端按商品天数判定，不能由前端决定。
- [重复请求重复扣费] → 独立 `web_answer` usage kind 与现有唯一 usage ID 约束。
- [隐私泄露] → 最小化查询、服务端密钥、日志脱敏、不保存原始网页内容。

## Migration Plan

1. 增加数据库迁移，允许 `web_answer` 用量类型，并增加联网计费/来源字段。
2. 部署配置但保持 `OFFERSTEADY_WEB_SEARCH_ENABLED=false`，验证普通回答不受影响。
3. 开启内部测试账号，验证搜索、来源、会员和积分结算。
4. 确认国服无进行中面试后滚动部署；若搜索网关异常，关闭配置即可回退旧链路。
5. 观察详细回答耗时、搜索失败率、积分流水和 API P95，再决定是否扩大开放。

## Open Questions

- 生产使用阿里云 Responses API 的哪个地域/Workspace？当前账号是否已开通 `web_search`。
- 搜索来源是否需要在回答下方默认展开，还是默认折叠。
- Global 服是否后续采用单独的联网额度，而不是国内积分。
