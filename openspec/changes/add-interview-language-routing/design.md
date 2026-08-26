## Context

当前 Web 创建草稿时只提交标题，准备页管理材料和桌面设备；后端 `InterviewSessionRecord` 没有语言字段。DashScope Realtime ASR 的 `session.update.input_audio_transcription.language` 被固定为 `zh`，Chat Service 的 system/quick/detail/continuation Prompt 由固定中文文件加载，Screenshot Answer 也使用固定中文模板和中文用户段落。语言因此散落在供应商适配器、Prompt 文件与代码常量中，客户端也无法在刷新后恢复选择。

本变更跨越 Web、会话 API/存储、实时 ASR、问题检测、聊天、截图和 AI 评测。语言必须成为服务端会话的权威事实，避免音频请求、回答请求或旧客户端各自携带不同语言造成链路分裂。简历、JD、转录和截图仍属于敏感数据，本变更不扩大保存范围。

## Goals / Non-Goals

**Goals:**

- 在准备页提供默认中文、可选英文且可恢复的会话语言。
- 保证一个已开始会话的 ASR、问题识别、聊天和截图回答始终使用同一语言。
- 以独立、可评测、可版本化的英文 Prompt 实现自然英文答案，中文路径保持原样。
- 对历史数据、旧客户端、断线重连和灰度/回滚提供明确兼容行为。
- 提供足够的语言维度诊断，但不记录敏感正文。

**Non-Goals:**

- 不做导航、按钮、账单、资料管理等整个产品 UI 的英文国际化。
- 不支持同一场面试进行中切换语言、自动语言检测或中英混合逐轮路由。
- 不翻译或重写已存简历、JD、知识材料和历史转录。
- 不更换 ASR/LLM 供应商，也不把语言判断放进桌面伴随程序。
- 不因本功能改变音频、截图或个人资料的保存与授权策略。

## Decisions

### 1. Store a closed interview-language enum on the authoritative session

在 `InterviewSessionRecord`、API response 和持久化表中增加 `interview_language`，领域类型只允许 `zh-CN | en-US`。数据库列使用非空默认 `zh-CN` 并回填已有记录。新建会话可接受可选语言，但未传时由服务端赋值 `zh-CN`；准备态通过独立的所有权校验命令更新。`start_session` 与语言更新都依据持久化状态约束，非 `preparing` 更新返回稳定业务错误。

选择服务端会话字段而不是浏览器 localStorage 或每个请求传 `language`，是为了保证刷新、跨设备、重连、自动触发与截图任务使用同一事实，也避免未授权请求绕过已选语言。重新开始会话复制原语言，但新会话仍处于准备态。

### 2. Treat language as content configuration, not application locale

Web 在准备页增加两项可访问的单选控件：“中文面试”和“English Interview”，初始化与切换结果均来自会话 API。有效默认值不会成为新的 readiness 数量或确认步骤；保存失败时回滚到服务端确认值。进入 `live` 后只读显示语言。

备选方案是同步把所有界面翻译成英文，但这会引入完整 i18n、文案和可访问性范围，且与“英文面试内容”不是同一需求，因此留待独立变更。

### 3. Resolve language once from the session at every server-side entry point

Realtime Speech、Chat Service、Screenshot Answer 和问题识别入口先通过 `SessionService` 获取有所有权校验的会话，再把已锁定语言传给内部适配器。音频帧、手动问题和截图请求不接受可覆盖语言。运行时对象与 ASR source-session identity 保存语言；如果缓存对象语言与权威会话不一致则关闭并重建，绝不复用另一语言的连接。

这种显式传递比进程全局语言或请求上下文隐式变量更容易测试，也不会在并发会话之间串扰。

### 4. Map the domain enum to provider-specific ASR configuration inside the adapter

领域层使用稳定的 `zh-CN` / `en-US`，DashScope adapter 在 `session.update` 边界映射为供应商接受的 `zh` / `en` 配置。预热、首次连接和重连都调用同一个映射。供应商以后变化时只替换 adapter mapping，不把供应商枚举泄漏到 Web 或会话数据。

备选方案是让 ASR 自动检测语言。当前产品只承诺单场单语言，显式 hint 的延迟和确定性更好，也更容易定位 403、配置失败和识别质量问题，因此 MVP 不采用自动检测。

2026-08-26 供应商售后确认：`qwen3-asr-flash-realtime-2026-02-10` 当前只支持公共入口 `wss://dashscope.aliyuncs.com/api-ws/v1/realtime`，不支持 Workspace 专属 Host。生产因此保持公共 WebSocket，并通过 `model` 查询参数选择模型；Workspace Host 返回的 HTTP 403 属于该模型当前产品边界，不作为密钥或生产故障。生产实测公共入口可完成 `session.created` 与英文 `session.updated`，且未输出 API Key。

### 5. Use separate English prompt assets with a language-aware resolver

现有中文 Prompt 文件路径保持不变，以降低中文回归风险；在对应目录增加英语文件，例如 `system.en.md`、`quick.en.md`、`detail.en.md`、`continuation.en.md` 与 screenshot `system.en.md`。Prompt adapter 接受领域语言并返回带语言后缀的 template ID/version。英语文件缺失时 fail closed，不能回退中文。

Prompt Builder 中会影响模型或用户可见结果的中文运行时常量也必须进入语言资源，包括问题规范化协议周围的说明、快答/详答分隔语义、续写指令、截图摘要标签和默认截图指令。机器可解析的 XML 标记（如 `normalized_question`）跨语言保持不变，降低流式解析改动风险；前端展示标题可按会话语言选择，不能把中文标题混入英文答案正文。

没有选择“运行时把中文 Prompt 机器翻译为英文”，因为翻译结果不可版本化、增加延迟且难以做稳定评测。也没有把整份 prompt 复制进业务代码，以遵守 Prompt 集中管理规则。

### 6. Preserve evidence facts while controlling output language

英文会话可以使用中文或英文资料。检索仍基于原文与既有索引，Prompt 明确要求把可验证事实用英文表达、标记不确定性并禁止虚构候选人经历；不预先翻译或覆盖材料。截图中的原始题面、资料事实、模型推断和建议继续分层，最终建议使用会话语言。

### 7. Add language-aware tests, evals and telemetry

后端单元/集成测试覆盖持久化默认值、状态锁、所有权、重启继承、ASR payload/reconnect、聊天各阶段、截图和缺失模板失败；Web 测试覆盖默认选择、保存、刷新恢复、错误回滚与 live 只读。`ai/evals/` 新增合成或脱敏英语样本，覆盖英语问题规范化、双声道自动触发、快答/详答/续写、中文资料英文回答和截图回答，同时运行现有中文基线。

结构化日志和指标增加 `interview_language`、prompt template ID/version 与 stage，继续只记录哈希、长度和错误类别。禁止新增原始音频、截图、转录或完整问答日志。

## Risks / Trade-offs

- [英文口音和中英夹杂会降低显式英文 ASR 的召回率] → v1 明确单语言边界，用合成多口音样本和受控真人验收评估；混合语言另立变更。
- [散落的中文代码常量可能使英文输出混入中文] → 建立入口清单和集成测试，对用户可见回答正文做英文脚本检测，对机器标签单独豁免。
- [Prompt 文件缺失造成英文任务失败] → 启动/部署检查验证所有必需语言与阶段资产，运行时 fail closed，并在生产切流前执行 smoke test。
- [数据库与旧应用版本滚动部署期间字段不一致] → 先部署向后兼容迁移和后端，再部署 Web；后端对缺失字段默认为中文，回滚时保留新增列。
- [ASR 供应商英文语言码或模型权限与预期不同] → 在 adapter 测试和预生产连通性测试中验证实际 session update；错误记录 endpoint/model/status/code，不记录 API Key。
- [英语 Prompt 增加上下文或输出长度，影响首字延迟与成本] → 为语言分别记录首个 partial、首 token、总时长与 token 用量，在灰度门禁设置对比阈值。

## Migration Plan

1. 增加数据库列并回填 `zh-CN`；部署能够读写新字段但仍兼容旧 Web 请求的后端。
2. 部署全部英文 Prompt 资产和启动校验；在非生产环境验证普通回答、截图和 DashScope realtime ASR 的英文配置。
3. 运行中英文单元、集成、端到端和 AI eval 门禁，确认中文基线无回退。
4. 部署 Web 准备页选择器，先对内部账号开放英文入口，再逐步扩大流量。
5. 生产分别进行一场中文和一场英文双声道 smoke test，核对转录、问题触发、流式快答/详答/续写与截图回答。

回滚时先隐藏 Web 英文选择并停止新建 `en-US` 会话，允许已开始英文会话使用当前后端完成；如必须回滚后端，先结束或排空英文会话。数据库列保留且中文默认不变，避免破坏历史数据。桌面协议未改变，因此本变更不触发桌面版本号升级。

## Open Questions

- 英文回答的产品口吻（美式/英式、简洁程度）初版按中性商务英语设计，具体风格可在 AI eval 评审时调整，不影响数据模型和路由。
