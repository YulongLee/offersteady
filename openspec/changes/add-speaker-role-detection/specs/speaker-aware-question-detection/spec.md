## ADDED Requirements

### Requirement: Preserve audio-source identity
系统 MUST 在采集、传输、转录和问题检测过程中保留麦克风、系统音频或混合来源及其时间范围，并 SHALL 在双声道可用时独立处理麦克风和系统音频。

#### Scenario: Dual-channel audio arrives
- **WHEN** 桌面伴随程序同时发送麦克风和系统音频帧
- **THEN** 系统为每个转录片段保留来源 ID、来源类型、序列时间和会话关联

#### Scenario: Only mixed audio is available
- **WHEN** 运行环境只能提供单个混合音频源
- **THEN** 系统标记来源不可区分、关闭音频自动回答并在 Web 保留手动提问路径

### Requirement: Suppress echo and duplicate speech
系统 MUST 检测同一时间窗内跨声道的回声、高度相似音频或重复转录，并 MUST 避免将同一话语创建为多个独立说话轮次。

#### Scenario: Candidate voice loops into system audio
- **WHEN** 候选人麦克风语音随后以回声出现在系统音频
- **THEN** 系统保留候选人主片段、标记或抑制重复片段且不把回声识别成面试官问题

### Requirement: Diarize speakers within a session
系统 MAY 使用可替换适配器为系统音频片段分配会话内稳定的匿名 speaker ID，以支持去重和转录修订；所有远端 speaker 在用户界面中 MUST 统一呈现为“面试官”，且匿名 ID 不得成为新的用户角色。

#### Scenario: Two interviewers speak
- **WHEN** 系统音频中检测到两名稳定的不同说话人
- **THEN** 系统可保留不同 speaker ID 用于内部去重，但两者均显示为“面试官”

#### Scenario: Speakers overlap
- **WHEN** 两名参与者同时说话且无法可靠分离文本
- **THEN** 系统标记重叠与不确定性，并不得把该片段自动标为可靠问题

### Requirement: Map speakers to interview roles
系统 MUST 根据可信音频来源映射展示角色：本地麦克风或耳机来源为 `candidate`，系统音频来源为 `interviewer`。新事件不得创建用户可见的 `unknown` 角色，speaker ID 不得被解释为现实身份。

#### Scenario: Clean dual-channel conversation
- **WHEN** 麦克风只有候选人语音且系统声道只有远端参与者语音
- **THEN** 系统将麦克风片段显示为“我”、系统音频片段显示为“面试官”

#### Scenario: Channel evidence conflicts
- **WHEN** 同一 speaker 的语音同时出现在麦克风和系统音频且无法判定主来源
- **THEN** 系统执行回声或重复抑制；无法安全去重时停止该片段自动触发并显示来源降级，不展示第三角色

### Requirement: Present role-aware transcripts
Web 应用 SHALL 实时展示“我”和“面试官”两种角色，并 MUST 区分临时转录、最终转录和重叠状态。Web MUST NOT 展示角色置信度、角色待确认或角色修改操作。

#### Scenario: Interim transcript is revised
- **WHEN** 转录服务修订一条未最终确认的片段
- **THEN** Web 更新同一片段而不是追加新的说话轮次或问题

#### Scenario: Source cannot be trusted
- **WHEN** 转录事件缺少可信的麦克风或系统音频来源
- **THEN** Web 不把它显示为第三角色且不触发回答，而是在对话列表外显示来源降级状态

### Requirement: Detect complete interviewer questions
系统 SHALL 合并连续面试官话语并根据端点、句法完整性和问题意图检测可回答问题，不得只依赖问号或固定静音时间。

#### Scenario: Interviewer gives context before a question
- **WHEN** 面试官先描述背景再提出完整问题
- **THEN** 系统等待最终问题边界后生成一个包含必要上下文的问题候选

#### Scenario: Interviewer asks an imperative question
- **WHEN** 面试官说“讲讲你做过的性能优化”且话语边界已确认
- **THEN** 系统将其识别为问题意图，即使文本没有疑问标点

#### Scenario: Interviewer gives acknowledgement
- **WHEN** 面试官只说“好的”“明白”或其他非问题反馈
- **THEN** 系统不创建问题候选

### Requirement: Gate automatic answer triggering
系统 MUST 只为系统音频中的最终转录、完整问题意图且未重复的问题自动发布唯一确认事件；本地麦克风内容 MUST 被拒绝，文本或边界不清晰的问题 SHALL 保留手动确认或手动输入路径。

#### Scenario: High-confidence interviewer question completes
- **WHEN** 一段系统音频最终话语同时达到文本、完整性和问题阈值
- **THEN** 系统发布一次 `QuestionConfirmed` 并创建一条回答任务

#### Scenario: Candidate is answering
- **WHEN** 候选人 speaker 持续回答或反问澄清
- **THEN** 系统不自动创建面试回答任务

#### Scenario: Possible question has low confidence
- **WHEN** 系统音频文本可能是问题但转录、重叠或边界置信不足
- **THEN** 系统显示问题内容不清晰且不把它标为可靠回答触发，用户可改用手动输入

### Requirement: Deduplicate streaming revisions
系统 MUST 使用稳定片段 ID、revision、时间范围和来源片段集合去重，并 MUST 保证同一问题只产生一个回答触发和一个计费用量标识。

#### Scenario: Final transcript repeats interim words
- **WHEN** 最终转录包含此前多次发送的临时文本
- **THEN** 系统更新原片段和问题候选，不追加重复问题或重复扣费

#### Scenario: Confirmed question receives a text correction
- **WHEN** 已确认问题因最终转录修订而改变少量文字
- **THEN** 系统更新问题版本但不自动创建第二条回答，除非用户明确重新生成

### Requirement: Allow question correction without role correction
系统 SHALL 允许用户确认内容不清晰的问题、拒绝误触发问题和编辑问题文本，但 MUST NOT 要求用户纠正由声道固定决定的展示角色。

#### Scenario: User sees a source-routing error
- **WHEN** 用户发现音频来源不符合双声道约定
- **THEN** 系统提供检查桌面音频来源或切换手动输入的路径，而不提供“设为我/面试官”操作

#### Scenario: User confirms an uncertain question
- **WHEN** 用户检查并确认一条待定问题
- **THEN** 系统发布唯一确认事件并开始回答，而不要求重新输入完整问题

### Requirement: Degrade safely when detection is unavailable
系统 SHALL 在双声道来源、回声抑制或问题检测不可用时停止自动确认，保留已有转录和手动输入路径，并 MUST 明确展示降级状态。

#### Scenario: Diarization provider fails
- **WHEN** 来源能力检测只返回混合音频或系统无法区分两个输入
- **THEN** 系统不猜测第三角色，切换为手动输入且不停止用户已明确授权的可用采集

### Requirement: Minimize speaker data
系统 MUST 默认只在会话内短暂处理说话人特征，不得将 speaker embedding 用于现实身份识别或跨会话跟踪，并 MUST 在会话结束后删除临时特征。

#### Scenario: Interview session ends
- **WHEN** 用户结束面试
- **THEN** 系统删除会话内音频缓冲和临时 speaker 特征，仅按数据策略保留匿名角色事件与必要文本

### Requirement: Evaluate role and trigger quality
系统 MUST 使用合成或经过授权的数据评测来源路由、问题召回、候选人误触发、重复触发和端到端延迟，并 SHALL 在未达到发布阈值时保持自动确认关闭。

#### Scenario: Candidate false-trigger rate exceeds threshold
- **WHEN** 当前模型或配置在评测中把候选人语音误触发为问题的比例超过发布阈值
- **THEN** 系统不得为该配置启用自动确认，只允许手动模式
