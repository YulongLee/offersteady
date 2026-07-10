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

#### Scenario: Interruption ends a source stream
- **WHEN** source 结束、会话结束或连接超时
- **THEN** 系统优雅关闭对应 ASR 长连接并释放该 source 的流式资源

### Requirement: Audio transport SHALL send incremental chunks instead of repeated cumulative segments
系统 MUST 发送增量音频 Chunk，而不是在每次 interim 更新时重复发送同一段从头开始的累计音频。系统 MUST 为每个 source 维护顺序、时间戳和增量偏移，并 SHALL 支持后端按顺序重建流式音频上下文。

#### Scenario: Partial updates are emitted during continuous speech
- **WHEN** 用户持续说话并产生多个 Partial Transcript
- **THEN** 每次发送的音频负载只包含自上次成功发送后新增的音频数据，而不重复发送之前已发送的部分

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
- **THEN** 每个 source 的缓冲区保持有界增长，并避免因频繁分配对象导致明显 GC 抖动

### Requirement: Partial and final transcript delivery SHALL be streamed independently
系统 MUST 将 Partial Transcript 和 Final Transcript 视为两类不同实时事件处理。网页端 MUST 能先显示 Partial Transcript，再在 Final Transcript 到达时原地更新同一句内容，而不是把每次更新都当成独立新句插入。

#### Scenario: Partial transcript arrives before the final transcript
- **WHEN** 某一句话先产生 Partial Transcript，随后产生 Final Transcript
- **THEN** 网页端先展示 Partial Transcript，并在 Final Transcript 到达后原地替换该句的内容和状态

#### Scenario: Partial transcript is superseded by a newer partial
- **WHEN** 同一句话收到更新版本的 Partial Transcript
- **THEN** 网页端覆盖旧 partial，而不是在实时对话区叠加重复句子

### Requirement: Invalid silence and phantom transcript generation SHALL be suppressed
系统 MUST 对静音、底噪、无效系统噪声和空白识别结果进行抑制。系统 MUST NOT 因为空白文本、低幅环境噪声或未达阈值的输入而持续生成新的实时字幕事件。

#### Scenario: User remains silent while microphone stays open
- **WHEN** 麦克风处于打开状态但用户未说话
- **THEN** 系统不生成新的实时字幕，也不把静音误判为连续说话

#### Scenario: ASR returns an empty or whitespace-only partial result
- **WHEN** ASR 返回空白、仅空格或无有效文本的 partial/final 结果
- **THEN** 系统丢弃该结果，不更新实时对话区
