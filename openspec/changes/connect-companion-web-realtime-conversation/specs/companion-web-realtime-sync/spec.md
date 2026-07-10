## ADDED Requirements

### Requirement: Companion audio SHALL map to two realtime transcript roles
系统 MUST 将桌面伴随助手采集的双通道音频映射到当前面试 session 的两类实时转录角色：麦克风/耳机输入 MUST 作为“我”，电脑输出音频 MUST 作为“面试官”。系统 MUST 仅接受显式声明来源的音频帧，MUST NOT 将未知来源混入实时对话。

#### Scenario: Microphone frame is accepted as candidate speech
- **WHEN** 桌面伴随助手向当前面试 session 发布来源为 `microphone` 的音频帧
- **THEN** 后端将该帧转写为当前 session 的“我”角色实时转录

#### Scenario: System audio frame is accepted as interviewer speech
- **WHEN** 桌面伴随助手向当前面试 session 发布来源为 `system` 的音频帧
- **THEN** 后端将该帧转写为当前 session 的“面试官”角色实时转录

#### Scenario: Unknown or mixed source is rejected for realtime conversation
- **WHEN** 音频帧未声明合法来源，或以混合来源尝试写入实时对话
- **THEN** 系统拒绝将该帧写入当前 session 的实时对话，并返回可诊断失败状态

### Requirement: Web live conversation SHALL show only current-session realtime transcripts
用户进入面试页后，网页实时对话区 MUST 展示当前面试 session 的真实实时转录，并 MUST 过滤掉其他 session、历史遗留记录或未完成绑定的设备事件。实时对话区 MUST 以“面试官 / 我”角色顺序渲染当前会话内容。

#### Scenario: User enters a live interview with an active companion binding
- **WHEN** 当前面试 session 已开始，且桌面伴随助手已通过当前机器码绑定并开始发布当前 session 的实时音频
- **THEN** 网页实时对话区显示当前 session 的“面试官 / 我”转录内容

#### Scenario: Historical transcripts exist for another session
- **WHEN** 后端中存在其他面试 session 的历史转录
- **THEN** 网页实时对话区只展示当前 session 的实时转录，不展示其他 session 的内容

#### Scenario: Companion is not bound to the current session
- **WHEN** 用户进入面试页但桌面伴随助手没有绑定当前 session
- **THEN** 网页实时对话区保持空态或等待态，而不是展示历史转录

### Requirement: Realtime sync SHALL expose stage-specific diagnostics
系统 MUST 为桌面助手、后端和网页之间的实时链路提供可区分的诊断状态，至少区分设备未采集、帧未上传、ASR 未返回、网页未消费和 session 绑定失效五类问题。诊断信息 MUST 指向当前 session，且 MUST NOT 暴露原始音频内容。

#### Scenario: Device capture is unavailable
- **WHEN** 桌面伴随助手未产生麦克风或电脑输出的有效帧
- **THEN** 实时链路状态显示设备采集不可用，而不是误报为网页或 ASR 故障

#### Scenario: Backend receives frames but ASR does not accept them
- **WHEN** 后端已经收到当前 session 的音频帧，但转录未成功生成
- **THEN** 系统将链路状态标记为 ASR 阶段失败，并保留当前 session 的设备连接上下文

#### Scenario: Web page does not consume current-session transcripts
- **WHEN** 后端已经为当前 session 生成转录，但网页实时对话区未显示
- **THEN** 系统将链路状态标记为网页消费失败或同步延迟，而不是清空设备状态
