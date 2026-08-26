## ADDED Requirements

### Requirement: Interview language SHALL be an authoritative session setting
系统 SHALL 为每场面试保存且返回一个 `interviewLanguage`，值 MUST 仅为 `zh-CN` 或 `en-US`。未显式选择的新会话、迁移前已有会话和未携带该字段的兼容请求 MUST 解析为 `zh-CN`；服务端 MUST NOT 接受任意语言字符串或由回答、截图、音频请求临时覆盖会话语言。

#### Scenario: New session uses the compatibility default
- **WHEN** 用户创建面试且客户端未显式提交语言
- **THEN** 服务端将该会话保存为 `zh-CN` 并在后续会话响应中返回该值

#### Scenario: User selects English during preparation
- **WHEN** 会话仍处于 `preparing` 且所有权校验通过，用户将语言改为 `en-US`
- **THEN** 服务端持久化 `en-US`，刷新或重新进入后仍返回同一值

#### Scenario: Unsupported language is submitted
- **WHEN** 客户端提交不属于 `zh-CN` 或 `en-US` 的语言值
- **THEN** 服务端拒绝请求且不改变已保存的会话语言

### Requirement: Interview language SHALL be locked when the interview starts
系统 MUST 只允许会话所有者在 `preparing` 状态修改面试语言；会话进入 `live` 或 `ended` 后，语言 MUST 保持不变。重新开始一场面试时，新会话 SHALL 继承原会话语言，并允许用户在新会话开始前重新选择。

#### Scenario: Live session language update is attempted
- **WHEN** 用户或旧客户端尝试修改一场 `live` 会话的语言
- **THEN** 服务端拒绝修改，当前 ASR 和 AI 链路继续使用已锁定语言

#### Scenario: Ended interview is restarted
- **WHEN** 用户从一场英文面试创建“重新开始”会话
- **THEN** 新会话初始语言为 `en-US`，状态为 `preparing`，且开始前仍可修改

### Requirement: Realtime ASR SHALL follow the locked interview language
实时语音服务 MUST 从服务端会话读取语言，为每个 session/source 的 ASR 会话应用对应供应商语言配置，并在连接预热、断线重连和 source 重建时保持一致。中文会话 SHALL 继续使用当前中文识别行为；英文会话 SHALL 使用英文识别且不得为了展示而自动翻译成中文。不同语言的识别会话 MUST NOT 共享连接或缓存状态。

#### Scenario: English system audio is transcribed
- **WHEN** `en-US` 面试的系统音频包含英语面试官问题
- **THEN** ASR 以英语配置识别并发布英文 partial/final 转录，final 原位替换同一 segment 的 partial

#### Scenario: English ASR connection reconnects
- **WHEN** 英文会话的某个 source 因网络或供应商连接关闭而重建
- **THEN** 新连接继续携带英文配置且不会退回中文默认值

#### Scenario: Chinese session uses the existing path
- **WHEN** `zh-CN` 面试产生与现有中文基线相同的音频输入
- **THEN** 系统继续使用当前中文 ASR 配置、双声道角色路由和转录交付行为

### Requirement: Question handling SHALL use the session language
问题边界检测、问题规范化、自动触发和低置信度确认 MUST 以会话语言为准。英文链路 MUST 识别英语问句、英文陈述和英语口语省略，不得依赖仅适用于中文的标点、短句或关键词规则；候选人麦克风内容仍 MUST NOT 自动触发回答。

#### Scenario: English interviewer asks a complete question
- **WHEN** `en-US` 会话收到系统音频 final 转录 “Tell me about a difficult production incident you handled.”
- **THEN** 系统将其规范化为英文问题并创建一次回答任务

#### Scenario: Candidate speaks English
- **WHEN** `en-US` 会话收到候选人麦克风的英文回答
- **THEN** 系统展示英文转录但不自动创建回答任务

#### Scenario: English statement is not a question
- **WHEN** 英文系统音频只包含寒暄或不完整陈述且未满足问题确认规则
- **THEN** 系统不自动创建回答，或按既有低置信度流程要求用户确认

### Requirement: All generated interview assistance SHALL use versioned language-specific prompts
聊天快答、详答、截断续写、普通非流式回答和截图回答 MUST 由同一会话语言选择独立、版本化的服务端 Prompt Template。`en-US` 模板 MUST 以自然、可直接口述的英文生成内容；`zh-CN` MUST 继续加载现有中文模板。英文模板缺失或不可读时系统 MUST 明确失败并记录非敏感错误，不得静默回退到中文或在运行时机器翻译中文 Prompt。

#### Scenario: English quick and detailed answer streams
- **WHEN** 英文会话提交一个自动或手动问题
- **THEN** 快答、详答和必要续写均使用英文模板，流式边界保持有效，最终正文为英文

#### Scenario: English screenshot answer is requested
- **WHEN** 英文会话提交一张包含编程题或系统设计题的截图
- **THEN** 截图识别和回答链路使用英文模板并返回英文建议，同时明确区分截图原始信息、资料事实和 AI 建议

#### Scenario: English source uses Chinese personal materials
- **WHEN** 英文会话选用了中文简历、JD 或知识材料
- **THEN** 系统保留其中可验证的事实并用英文作答，不得虚构翻译不确定的经历或把资料原文改写为新的事实

#### Scenario: English prompt asset is unavailable
- **WHEN** 服务端无法加载英文模式所需的某个 Prompt Template
- **THEN** 对应任务以可恢复错误结束，且不会调用中文模板生成结果

### Requirement: Language routing SHALL be observable without logging sensitive content
系统 SHALL 为 ASR 建连、问题处理、回答任务和截图任务记录规范化语言枚举及 Prompt 模板标识/版本，并 MUST 保持现有的内容哈希或长度级日志策略，不得新增完整音频、转录、截图、问题、回答或个人材料日志。

#### Scenario: Operations inspect an English failure
- **WHEN** 一次英文 ASR 或回答任务失败
- **THEN** 诊断信息能区分 `en-US`、处理阶段、供应商错误类别和模板版本，但不包含完整敏感内容

### Requirement: Chinese behavior SHALL remain regression protected
引入英文分支后，中文默认值、当前中文提示词路径、实时双声道路由、流式回答和截图回答 MUST 保持现有可观察行为。发布门禁 MUST 同时运行中英文测试与 AI 评测，不能只验证英文新增路径。

#### Scenario: Existing client starts an interview
- **WHEN** 未识别新字段的旧 Web 客户端按原请求创建并开始会话
- **THEN** 服务端将其作为中文面试处理且现有主链路可以继续工作

#### Scenario: Release candidate is evaluated
- **WHEN** 语言分支版本准备发布
- **THEN** 中文回归基线与英文 ASR、问题规范化、快答、详答、续写和截图评测均通过后才允许切换生产流量
