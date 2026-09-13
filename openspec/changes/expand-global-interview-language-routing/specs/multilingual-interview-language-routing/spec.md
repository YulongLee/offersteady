## ADDED Requirements

### Requirement: Offer a controlled multilingual locale registry
国际版 MUST 从版本化 locale registry 提供面试语言选项。每个可选 locale MUST 包含显示名称、ASR provider code、回答输出语言标签和 release tier；客户端 MUST NOT 接受任意未注册语言字符串。

#### Scenario: User opens language selector
- **WHEN** 用户在创建或准备国际版面试
- **THEN** 系统展示 registry 中可用语言，并明确区分 Production 与 Beta，不改变现有页面布局和 readiness 计算

#### Scenario: Client submits an unknown locale
- **WHEN** 客户端提交 registry 之外的语言值
- **THEN** 后端拒绝请求并返回稳定的无敏感内容错误，不创建或修改会话语言

### Requirement: Persist a default language and a session language independently
系统 MUST 在用户设置中保存默认面试语言，并在创建草稿时使用它；准备阶段允许用户覆盖当前会话语言。会话开始后语言 MUST 锁定，刷新、重新进入和重连 MUST 恢复同一值。

#### Scenario: New interview uses user default
- **WHEN** 用户已将默认面试语言设为日语并创建新面试
- **THEN** 新草稿以日语初始化，准备页显示日语且其他 readiness 条件保持不变

#### Scenario: User overrides one draft
- **WHEN** 用户在准备页将当前草稿从英语切换为法语并保存
- **THEN** 该草稿保存法语，用户默认语言和其他草稿不改变

#### Scenario: Active session language is locked
- **WHEN** 面试已经开始后请求修改语言
- **THEN** 后端拒绝修改，实时工作区继续显示已锁定语言

### Requirement: Route every session stage from the authoritative locale
ASR、问题识别与规范化、快答、详答、续写、截图回答、复盘和导出 MUST 使用同一会话 locale；请求体、音频帧和截图命令 MUST NOT 覆盖它。

#### Scenario: Reconnect preserves locale
- **WHEN** 日语会话的 ASR 连接断开并重连
- **THEN** 重连使用日语 provider code 和同一语言的识别/回答路由

#### Scenario: Cross-language override is attempted
- **WHEN** 英语会话的手动问题请求携带中文覆盖字段
- **THEN** 服务端忽略或拒绝覆盖字段，并按英语会话语言处理

### Requirement: Fail safely when a locale is not ready
当 locale 的 ASR 权限、provider code、提示词资源或评测门禁不满足时，系统 MUST 阻止该语言开始新会话或明确标记为 Beta；不得静默回退到中文或英文。

#### Scenario: Missing production prompt
- **WHEN** 用户选择一个缺少详答提示词的 production locale
- **THEN** 系统阻止开始并提示切换到已验证语言，同时记录 locale、阶段和错误类别而不记录用户内容
