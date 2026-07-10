## ADDED Requirements

### Requirement: Provider-aware realtime ASR telemetry
系统 MUST 为每个实时音频来源记录与 provider 调用直接相关的运行指标，至少包括连接重建次数、append 发送次数、commit 完成情况、partial 首字时间、final 完成时间、空白结果抑制次数、VAD/Manual 模式状态和 provider 错误分类。

#### Scenario: Runtime is queried during an active session
- **WHEN** 桌面端或网页端查询当前面试会话的 realtime runtime 状态
- **THEN** 系统返回与每个来源对应的 provider-aware 指标摘要，而不要求调用方读取底层日志

#### Scenario: Blank partials are suppressed
- **WHEN** provider 返回被系统判定为不可发布的空白或噪声 partial
- **THEN** 系统增加对应抑制计数，并让该次抑制可在 runtime diagnostics 中被观察到

#### Scenario: Provider mode fallback happens
- **WHEN** 某一路来源从 provider VAD 模式回退到 Manual commit 模式
- **THEN** runtime diagnostics 记录该来源的模式变化与触发原因，便于后续定位 provider 调用问题

### Requirement: Performance baseline SHALL be reproducible locally
系统 MUST 提供本地可重复执行的基线验证方式，用于记录当前 Realtime ASR pipeline 的关键延迟与 provider 行为指标。该基线 MUST 可用于后续优化前后对比。

#### Scenario: Team runs the benchmark flow
- **WHEN** 开发者执行项目定义的 realtime ASR benchmark 流程
- **THEN** 系统生成包含关键延迟与 provider counters 的基线结果文件，供后续优化对比使用

### Requirement: Provider errors SHALL be diagnosable without exposing sensitive audio
系统 MUST 将 provider 失败分类为可操作的错误原因，例如连接失败、`session.created` 缺失、session 初始化失败、append 超时、commit 超时、completed 缺失、VAD 异常或返回无效结果。系统 MUST NOT 在诊断输出中记录原始音频正文或敏感语音内容。

#### Scenario: Provider session update fails
- **WHEN** provider session 初始化或更新失败
- **THEN** runtime diagnostics 和日志展示结构化错误类别与来源信息，但不包含原始音频内容

#### Scenario: Operator reviews integration failure
- **WHEN** 开发者排查实时语音失效问题
- **THEN** 系统提供足够的 provider 状态、延迟和错误码来定位问题，而无需依赖用户提供音频原文
