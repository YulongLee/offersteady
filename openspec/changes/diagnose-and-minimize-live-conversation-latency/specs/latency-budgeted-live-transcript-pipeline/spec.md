## ADDED Requirements

### Requirement: Enforce a budgeted low-latency transcript pipeline
系统 MUST 为实时字幕链路定义明确的延迟预算，并 MUST 优先保证 partial transcript 的低延迟可见性。系统 MUST 至少跟踪首字延迟、partial 更新延迟、final 完成延迟和前端可见延迟，并在连续超标时触发异常状态。

#### Scenario: Partial transcript arrives within budget
- **WHEN** 用户开始说话且音频已经进入实时链路
- **THEN** 系统优先展示最近可用的 partial transcript，并用该事件计算首字延迟和可见延迟

#### Scenario: Final transcript exceeds budget
- **WHEN** partial 已经出现但 final transcript 长时间未到达
- **THEN** 系统保留当前 partial 可见状态，同时将该路 source 标记为 final 完成延迟超标

### Requirement: Deliver audio incrementally instead of accumulating long utterances
桌面端与后端之间的实时语音链路 MUST 采用增量 PCM chunk 传输，而不是累计整句或整段音频后重复发送。后端 worker MUST 基于增量数据持续喂给 provider session，并避免重复处理已经发送过的音频帧。

#### Scenario: User continues speaking
- **WHEN** 用户持续说话超过一个 chunk 周期
- **THEN** 桌面端逐步发送新的音频 chunk，后端不会等待整句结束后才把整段音频送去识别

#### Scenario: Existing audio was already sent
- **WHEN** 某一段 PCM 数据已经成功进入当前 source 的 provider 会话
- **THEN** 系统不会因为后续 partial / final 更新而把相同音频重新累计上传

### Requirement: Separate partial rendering from final persistence
系统 MUST 将 partial transcript 的实时显示与 final transcript 的稳定归档解耦。partial transcript SHALL 用于快速更新对话区，final transcript MUST 用于稳定记录、后续问题识别和上下文沉淀。过期、空白或被更新覆盖的 partial transcript MUST NOT 被当作正式历史消息持久化。

#### Scenario: Partial text keeps changing
- **WHEN** 同一路 source 在一个未结束发言期间持续收到新的 partial transcript
- **THEN** 前端覆盖最近一条未完成字幕，而不是为每次 partial 创建新的历史行

#### Scenario: Final transcript arrives
- **WHEN** provider 返回某一路 source 的 final transcript
- **THEN** 系统将最近对应的 partial 转为稳定消息，并只对 final 执行正式归档和后续业务触发

#### Scenario: Blank partial is suppressed
- **WHEN** provider 返回空白、纯噪声或已过期的 partial transcript
- **THEN** 系统抑制该 partial 的页面显示和正式落库，同时记录一次抑制计数

### Requirement: Use bounded asynchronous stages to avoid backlog amplification
后端 ingest、provider worker 和 transcript publish MUST 采用异步分层处理，并且每层 MUST 具备可观测的队列长度、等待时长和积压状态。系统在积压超阈值时 MUST 优先丢弃过期 partial 或合并微小更新，而不是让实时对话无限滞后。

#### Scenario: Provider pipeline is briefly slower than input
- **WHEN** 某一路 source 的送音速度短时间快于 provider 返回速度
- **THEN** 系统记录该阶段积压并优先压缩过期 partial 更新，而不是把用户看到的字幕整体拖慢几十秒

#### Scenario: Final transcript is pending
- **WHEN** 队列中同时存在未显示的过期 partial 和较新的 final / fresh partial
- **THEN** 系统保留 final 和最新有效 partial 的优先级，不因旧数据阻塞新结果展示
