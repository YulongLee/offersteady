## ADDED Requirements

### Requirement: Realtime audio ingestion SHALL use a non-blocking streaming pipeline
系统 MUST 将实时语音链路拆分为非阻塞流水线，而不是在音频接收路径上同步等待 ASR 完成。桌面采集端、后端接收端、ASR 客户端和网页消费端 MUST 通过明确的流式边界交接数据，任一阶段的暂时抖动 MUST NOT 阻塞上一阶段继续生产或接收音频。

#### Scenario: Audio frame arrives while prior transcript is still processing
- **WHEN** 当前 source 的新音频 Chunk 到达，而上一批 Chunk 对应的 Partial Transcript 仍在处理中
- **THEN** 系统继续接收并排队该 Chunk，而不是在接收路径上同步阻塞等待上一批识别完成

#### Scenario: Backend receives a burst of short audio chunks
- **WHEN** 用户连续说话导致多个短音频 Chunk 在极短时间内进入服务端
- **THEN** 后端按 source 和 session 将其送入独立流式处理队列，并保持接收接口快速返回

### Requirement: Realtime ASR client SHALL keep persistent session-scoped connections
系统 MUST 为每个当前面试 session 的每个实时音频 source 维持持久化 ASR 长连接，并 MUST 在同一 source 的连续语音过程中复用该连接。系统 MUST NOT 为同一 source 的每个 interim/final 片段频繁创建新的 WebSocket 或等价会话。

#### Scenario: Candidate keeps speaking across multiple partial updates
- **WHEN** 同一麦克风 source 在一次连续发言中产生多个 Partial Transcript 更新
- **THEN** 系统复用该 source 对应的持久化 ASR 连接，而不是为每次更新新建连接

#### Scenario: Provider emits a partial while the next audio chunk is being produced
- **WHEN** ASR 供应商在桌面端继续采集和发送后续增量音频期间返回 Partial Transcript
- **THEN** source 常驻接收器并行消费该事件并发布新 revision，音频发送线程不因等待 `recv` 而停止追加 PCM

#### Scenario: Partial arrives between two source worker calls
- **WHEN** provider partial 在上一批音频处理返回后、下一批音频任务开始前到达
- **THEN** 系统通过独立 delivered revision 游标在下一次交付中发布该 partial，且不得将它误判为已消费事件

#### Scenario: Interruption ends a source stream
- **WHEN** source 结束、会话结束或连接超时
- **THEN** 系统优雅关闭对应 ASR 长连接并释放该 source 的流式资源

#### Scenario: Consecutive local utterances use a healthy provider task
- **WHEN** 实验性持续 task 开关显式开启、同一 source 连续完成多个本地 utterance 且 Provider 为每句返回 `sentence_end`
- **THEN** 系统复用同一 WebSocket 和同一 Qwen task，不在每句之间执行 `finish-task` 与 `run-task`

#### Scenario: Production uses the provider-safe task lifecycle
- **WHEN** 生产使用默认配置处理同一 source 的连续 utterance
- **THEN** 系统复用同一 WebSocket，为当前句完成 `finish-task → task-finished` 后保持无活动 task 的空闲连接，并在下一句话首个音频帧到达时执行 `run-task → task-started → append PCM`，不得留下会在约 23 秒空闲后失败的活动 provider task

#### Scenario: Source session is prewarmed before speech
- **WHEN** 面试准备或连接恢复流程预热某个 source，但该 source 尚无音频帧
- **THEN** 系统只建立可复用的 Provider WebSocket，不启动 Qwen task；首个音频帧到达后才在该连接上启动本句 task

#### Scenario: Provider sentence finalization is missing
- **WHEN** 本地 final 到达但 Provider 未在有界时间内返回对应 `sentence_end`
- **THEN** 系统回退到 `finish-task → task-finished → run-task` 的兼容路径，并保持下一句可继续识别

#### Scenario: Provider task failure is followed by socket close
- **WHEN** Provider 先发送包含 code/message 的 `task-failed`，随后关闭 WebSocket
- **THEN** 系统保留首个 Provider 错误及 source/task/connection 归因，连接关闭不得将其覆盖为通用错误

#### Scenario: One source fails while the other remains healthy
- **WHEN** microphone 或 system 任一 source 发生可恢复 ASR 故障
- **THEN** 系统只重建该 source，publisher 与另一 source 继续接收音频

### Requirement: Audio transport SHALL send incremental chunks instead of repeated cumulative segments
系统 MUST 发送增量音频 Chunk，而不是在每次 interim 更新时重复发送同一段从头开始的累计音频。系统 MUST 为每个 source 维护顺序、时间戳和增量偏移，并 SHALL 支持后端按顺序重建流式音频上下文。

#### Scenario: Partial updates are emitted during continuous speech
- **WHEN** 用户持续说话并产生多个 Partial Transcript
- **THEN** 每次发送的音频负载只包含自上次成功发送后新增的音频数据，而不重复发送之前已发送的部分

#### Scenario: Continuous speech reaches the first partial boundary
- **WHEN** 任一有效 source 持续产生可识别语音
- **THEN** 桌面端约每 `100ms` 提交一次新增 PCM，并保持同一 utterance 的稳定 segment identity 与递增 revision

#### Scenario: Final transcript closes the utterance
- **WHEN** 一段话结束并产生 Final Transcript
- **THEN** 系统只为尚未发送的尾部音频发送 final 标记，而不是重新上传整段语音

### Requirement: Producer-Consumer buffering SHALL preserve low latency under burst traffic
系统 MUST 使用适合实时流的 Producer-Consumer 音频缓冲架构，并 SHALL 通过 RingBuffer、单 source 队列或等价机制降低频繁对象创建、重复内存拷贝和跨阶段争用。系统 MUST 定义背压策略，使延迟目标优先于保留过期 interim 结果。

#### Scenario: Consumer lags behind during a transient spike
- **WHEN** 短时间内转写速度落后于采集速度
- **THEN** 系统优先丢弃或覆盖过期 interim 工作单元，只保留最新可见状态和必要的 final 完整性

#### Scenario: Source queue stays healthy during normal speech
- **WHEN** 语音输入处于正常节奏
- **THEN** 每个 source 的缓冲区保持有界增长，当前约 `100ms` PCM 帧立即进入 ASR sender，不为追求合并而主动领取后续帧，并避免因频繁分配对象导致明显 GC 抖动

#### Scenario: Source queue develops a transient backlog
- **WHEN** 同一 source 已有多个待处理 PCM 帧形成明确积压
- **THEN** worker 才逐级合并相邻增量帧以追赶实时位置，完整保留音频字节和 Final，且不得等待凑满批次

#### Scenario: A long utterance reconnects after exceeding replay capacity
- **WHEN** 一个 segment 的音频超过重放容量后发生 Provider 断线
- **THEN** 系统重放最近的有界 PCM 尾部，并将恢复结果与内存中的已发布字幕检查点去重拼接，不得因缓存溢出放弃恢复或让可见字幕回缩

### Requirement: Partial and final transcript delivery SHALL be streamed independently
系统 MUST 将 Partial Transcript 和 Final Transcript 视为两类不同实时事件处理。网页端 MUST 能先显示 Partial Transcript，再在 Final Transcript 到达时原地更新同一句内容，而不是把每次更新都当成独立新句插入。

#### Scenario: Partial transcript arrives before the final transcript
- **WHEN** 某一句话先产生 Partial Transcript，随后产生 Final Transcript
- **THEN** 网页端先展示 Partial Transcript，并在 Final Transcript 到达后原地替换该句的内容和状态

#### Scenario: Partial transcript is superseded by a newer partial
- **WHEN** 同一句话收到更新版本的 Partial Transcript
- **THEN** 系统在同一 utterance 中立即应用正常增长或有界可变尾部纠错，保留已稳定前缀且不叠加重复句子

#### Scenario: A longer provider revision rewrites stable visible text
- **WHEN** 更新的 Partial 虽然同长或更长，但在有界可变尾部之前修改了已展示正文
- **THEN** 后端不得以“文本更长”为由整段替换已稳定内容，并继续以原 revision 速度发布后续合法增长

#### Scenario: Provider continues growing after rewriting an early token
- **WHEN** Provider 的完整假设改写了稳定前缀，随后在该修订或下一修订继续增加句尾文字
- **THEN** 后端保留已展示正文并仅追加相对上一版 Provider 假设确认新增的后缀，不得覆盖既有文字，也不得因前缀分歧冻结该 utterance 的后续增长

#### Scenario: Provider temporarily retracts before resuming growth
- **WHEN** Provider 临时返回较短假设，随后恢复上一完整假设并继续增加文字
- **THEN** 后端保留较长可见正文和上一完整 Provider 游标，恢复时只追加新增后缀，不得重复已有文字

#### Scenario: Provider emits several ordered partial revisions
- **WHEN** ASR 为同一 utterance 依次返回多个有效 Partial revision，且实时消费链路没有超过有界积压阈值
- **THEN** 后端 SSE 与网页状态层按 revision 顺序交付这些更新，不得无条件只保留最后一个 revision

#### Scenario: Provider partial enters the publication hot path
- **WHEN** 常驻 ASR 接收器收到一个有效 Partial Transcript
- **THEN** 后端仅执行当前 publisher、segment 和 revision 所需的有界读写后发布 transcript event，不得在发布前扫描该 session 的全部历史 transcript 或执行稳定问题识别

### Requirement: Invalid silence and phantom transcript generation SHALL be suppressed
系统 MUST 对静音、底噪、无效系统噪声和空白识别结果进行抑制。系统 MUST NOT 因为空白文本、低幅环境噪声或未达阈值的输入而持续生成新的实时字幕事件。

#### Scenario: User remains silent while microphone stays open
- **WHEN** 麦克风处于打开状态但用户未说话
- **THEN** 系统不生成新的实时字幕，也不把静音误判为连续说话

#### Scenario: ASR returns an empty or whitespace-only partial result
- **WHEN** ASR 返回空白、仅空格或无有效文本的 partial/final 结果
- **THEN** 系统丢弃该结果，不更新实时对话区

#### Scenario: Provider completes an utterance without transcript text
- **WHEN** ASR task 或 utterance 已正常完成，但静音、底噪或无效语音没有产生有效文本
- **THEN** 系统抑制该空结果、完成当前 segment，并复用健康 source 连接，不得降级 publisher、重试同一音频或重建 ASR WebSocket

#### Scenario: ASR returns a meaningful short Chinese response
- **WHEN** ASR 返回“好的”“是的”“对”“行”等具有明确语义的中文短句
- **THEN** 系统将该短句作为有效实时字幕发布，不得仅因字数较短或属于常见回答而抑制

### Requirement: Realtime subscription recovery SHALL avoid retry storms
网页端 MUST 在当前 session 的 SSE 通道健康时停止全量降级轮询，并 MUST 在连接中断时采用有上限的退避策略。身份失效或 session 不存在时，系统 MUST NOT 使用亚秒级固定间隔持续重试。

#### Scenario: Current realtime stream remains healthy
- **WHEN** 当前 session 的 SSE 通道持续收到有效快照
- **THEN** 网页不再执行周期性全量实时状态轮询

#### Scenario: Several partial revisions arrive within two seconds
- **WHEN** 当前 utterance 在两秒内产生多个 partial revision
- **THEN** SSE 继续及时推送字幕快照，但复用最近 runtime 诊断，不为每个 partial 重复执行完整运行态聚合

#### Scenario: Stream returns an authentication or missing-session response
- **WHEN** SSE 请求返回 `401`、`403` 或 `404`
- **THEN** 网页进入低频恢复探测，并在登录态、网络或有效 session 恢复后重建单一订阅

#### Scenario: A browser opens a realtime subscription before speech starts
- **WHEN** 当前 session 已授权且浏览器建立 SSE 连接
- **THEN** 后端在等待 Redis 事件或 runtime 诊断前立即发送完整 bootstrap snapshot，首快照不依赖新的语音或字幕事件

#### Scenario: An event is published while the bootstrap snapshot is materialized
- **WHEN** 后端已经取得 bootstrap cursor、尚未完成 snapshot 物化时产生新的 realtime event
- **THEN** snapshot 发出后，后端从该 bootstrap cursor 继续读取并交付该事件，不得因启动顺序丢失更新

#### Scenario: A healthy interview remains silent
- **WHEN** 没有新字幕但 SSE keepalive 持续到达
- **THEN** 浏览器保持当前唯一订阅，不执行首快照重试、全量轮询或重复重连

#### Scenario: A healthy stream stops delivering transport bytes
- **WHEN** 首 snapshot 已成功且连续超过两个 keepalive 周期没有收到任何 SSE 字节
- **THEN** 浏览器取消旧 reader，并由单一重连流程使用已保存 cursor 恢复，不清空当前字幕且不创建并行订阅

#### Scenario: Public reverse proxies deliver a realtime transcript revision
- **WHEN** Backend 为实时字幕 SSE 生成一个 snapshot、partial revision、final revision 或 keepalive 字节
- **THEN** 公网入口按事件即时 flush，且不得对该 SSE 响应执行 gzip、转换或聚合；普通页面和非 SSE 接口仍可启用响应压缩

### Requirement: Desktop device registration SHALL be stable and idempotent
桌面助手 MUST 为同一安装实例复用稳定设备身份。设备首次登记成功后，后续在线维持 MUST 使用 heartbeat，渲染进程 MUST NOT 周期性重复调用设备登记接口。

#### Scenario: Registered desktop remains open
- **WHEN** 已登记桌面助手持续运行并保持后端可达
- **THEN** 主进程周期性发送 heartbeat，设备登记事件不随 heartbeat 周期重复产生

### Requirement: Realtime publisher recovery SHALL reject stale credentials cleanly
后端 MUST 将重启后或已被替换的发布凭据作为 WebSocket 业务拒绝处理，MUST 使用可识别的终止码通知桌面端刷新凭据，并 MUST NOT 产生 ASGI 异常或高频异常日志。

#### Scenario: Desktop reconnects with a stale publisher token after backend restart
- **WHEN** 桌面助手使用重启前的 publisher token 重新连接实时音频 WebSocket
- **THEN** 后端发送 `publisher-credential-rejected` 事件并以 `1008` 关闭连接，桌面端进入既有凭据刷新流程，服务端不抛出二次断开或 HTTP-over-WebSocket 异常
