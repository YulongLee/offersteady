## ADDED Requirements

### Requirement: Measure live conversation latency across the full chain
系统 MUST 为每一场实时面试的实时对话链路建立端到端延迟诊断能力，覆盖桌面采集、桌面发送、后端接收、后端排队、provider 返回、事件发布、前端接收和前端渲染。诊断结果 MUST 能按 source（候选人 / 面试官）区分，并 MUST 能输出最近窗口的分段耗时与总耗时。

#### Scenario: Runtime exposes staged latency
- **WHEN** 一场面试已经开始并且某一路 source 正在持续送入音频
- **THEN** 系统返回该路 source 最近窗口内的 capture-to-send、send-to-ingest、ingest-to-worker、worker-to-partial、publish-to-receive 和 receive-to-paint 等分段耗时

#### Scenario: Two roles are measured independently
- **WHEN** 候选人和面试官两路音频同时存在
- **THEN** 系统分别统计两路 source 的链路延迟，而不是只输出单一全局耗时

### Requirement: Classify the dominant bottleneck instead of showing a generic delay message
当实时对话超出产品定义的延迟预算时，系统 MUST 输出明确的瓶颈分类和阶段状态，而不是只显示泛化文案。瓶颈分类 MUST 能区分桌面无音频、桌面发送积压、后端排队、provider partial 超时、provider final 超时、前端订阅停滞和前端渲染滞后。

#### Scenario: Desktop is not delivering frames
- **WHEN** 会话已绑定桌面伴随程序但后端在诊断窗口内未收到任何对应 source 的音频帧
- **THEN** 系统将状态归类为桌面无音频输入，并提示该路 source 尚未真实送音

#### Scenario: Provider is the slow stage
- **WHEN** 后端已经持续收到并消费音频帧，但 provider 长时间未返回 partial transcript
- **THEN** 系统将状态归类为 provider partial 超时，而不是错误地提示“未采集到有效音频”

#### Scenario: Frontend is the slow stage
- **WHEN** provider partial 已经发布但前端迟迟未接收或未绘制
- **THEN** 系统将状态归类为前端订阅或渲染滞后，并保留后台已收到 provider 结果的证据

### Requirement: Keep diagnostics privacy-safe
实时对话诊断 MUST 只记录时间戳、计数、阶段状态和错误分类，MUST NOT 为了诊断而新增原始音频持久化，也 MUST NOT 将完整敏感对话文本写入长期 profiling 日志。

#### Scenario: Diagnostics are collected
- **WHEN** 系统为实时面试生成链路诊断数据
- **THEN** 诊断数据仅包含耗时、次数、状态和错误类别，不新增原始音频长期保存

#### Scenario: Sensitive transcript exists
- **WHEN** 实时字幕本身已经在业务链路中存在
- **THEN** 诊断日志不因为性能分析而额外复制或长期落盘完整对话内容
