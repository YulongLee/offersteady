## ADDED Requirements

### Requirement: Source-scoped DashScope realtime sessions
系统 MUST 为每个实时面试会话中的每个音频来源（至少包括麦克风和电脑输出）维护独立的 DashScope Realtime ASR 长连接会话。系统 MUST 优先使用阿里百炼官方推荐的业务空间专属实时接入域名建立会话。系统 MUST NOT 为同一来源的每个 interim 或 final 片段重复建立新的 provider 会话。

#### Scenario: Microphone and system audio both publish
- **WHEN** 一场面试同时启用了麦克风和电脑输出两路音频
- **THEN** 系统为两路来源分别维护独立的 provider realtime session，而不是混用同一条 ASR 会话

#### Scenario: Same source sends multiple partial updates
- **WHEN** 同一来源在一次连续发言中产生多个 partial 更新
- **THEN** 系统复用该来源当前已建立的 provider realtime session，而不是为每次更新重新握手

#### Scenario: Dedicated workspace endpoint is configured
- **WHEN** 系统已配置阿里百炼业务空间专属实时 ASR 地址
- **THEN** provider session 使用该专属地址建立连接，而不是退回到公共兼容入口作为默认主路径

### Requirement: DashScope event flow SHALL use append then commit
系统 MUST 按 DashScope realtime 事件语义发送音频：连接建立后先等待 `session.created` 或等价就绪事件，再通过 `session.update` 初始化会话，增量音频通过 append 发送，utterance 完成后再 commit。系统 MUST NOT 通过重复上传累计整段音频来模拟 partial transcript。

#### Scenario: Source emits incremental audio
- **WHEN** 某一路来源持续采集到新的 PCM 音频帧
- **THEN** 系统只把尚未发送过的增量音频 append 到 provider 会话

#### Scenario: Utterance ends
- **WHEN** 某一路来源被判定当前一句话结束
- **THEN** 系统对该来源当前 provider 音频缓冲发送 commit，并等待 final transcript 或等价完成事件

#### Scenario: Session initialization starts
- **WHEN** 某一路来源首次建立 provider realtime session
- **THEN** 系统在 provider ready 后发送一次明确的 `session.update`，其中包含输入音频格式、采样率和转写配置

### Requirement: VAD and manual commit modes SHALL be provider-aware
系统 MUST 将阿里百炼 realtime ASR 的 VAD 与 Manual commit 模式视为可诊断的 provider 策略，而不是只依赖本地静音阈值。系统 SHALL 支持在会话初始化时显式配置 `turn_detection` 或等价 provider 参数，并在必要时从 VAD 回退到 Manual commit。

#### Scenario: Default live interview uses provider VAD
- **WHEN** 某场实时面试进入常规双通道语音模式
- **THEN** 系统优先按 provider VAD 模式初始化对应来源的 session，使 partial/final 识别尽早返回

#### Scenario: Provider VAD proves unstable
- **WHEN** 某一路来源出现持续误触发、异常静音或 provider VAD 不稳定
- **THEN** 系统允许该来源切换到 Manual commit 策略，并把这次模式回退记录到 runtime diagnostics

### Requirement: Partial and final transcripts SHALL be handled separately
系统 MUST 将 provider partial transcript 与 final transcript 作为两种不同状态处理。partial 用于实时显示和覆盖更新；final 用于稳定保存、上下文写入和问题检测。空白 partial 或无效 partial MUST 被抑制，不得污染最终 transcript 列表。

#### Scenario: Provider returns newer partial text
- **WHEN** provider 对同一条发言返回新的 partial text
- **THEN** 系统用新的 partial 覆盖旧的 partial 显示，而不是在实时对话中追加重复新行

#### Scenario: Provider returns final transcript
- **WHEN** provider 返回某条发言的 final transcript
- **THEN** 系统冻结该条文本、允许其进入稳定 transcript 列表，并让后续问题识别或回答触发只基于 final 内容执行

#### Scenario: Provider returns blank partial
- **WHEN** provider 返回空白、纯噪声或不可发布的 partial 结果
- **THEN** 系统丢弃该结果，不刷新实时对话显示，也不写入最终 transcript 存储

### Requirement: Provider session failures SHALL recover without breaking the interview page
系统 MUST 对 provider 建连失败、session 初始化失败、append 异常、commit 超时和 completed 缺失等错误进行分类处理。用户当前面试页 MUST 保持可继续使用，系统 SHALL 暴露可诊断状态并允许自动重试或受控回退。

#### Scenario: Provider connection drops mid-session
- **WHEN** 某一路来源的 provider realtime session 在面试中途断开
- **THEN** 系统记录该来源的错误状态，尝试按受控策略重连，并保持网页实时对话区和面试页不崩溃

#### Scenario: Provider final event is missing
- **WHEN** 某条发言的 commit 发送成功但在允许窗口内没有收到 final transcript
- **THEN** 系统将该次 provider 调用标记为可诊断失败，并不得把不完整的 partial 当作 final 写入稳定 transcript
