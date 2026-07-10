## ADDED Requirements

### Requirement: Prioritize low-latency partial and final transcript rendering
实时对话区 MUST 优先显示来自候选人和面试官两路 source 的最新 partial transcript，并在 final transcript 到达时稳定更新同一条对话记录。系统 MUST 让用户优先看到“正在说什么”，而不是等待整句完全结束后才整段出现。

#### Scenario: Speaker is still talking
- **WHEN** 某一路 source 已经开始返回 partial transcript 但 final 尚未完成
- **THEN** 实时对话区显示该路 source 的最新 partial 内容，并将其标记为进行中而不是空白等待

#### Scenario: Final transcript confirms the same utterance
- **WHEN** 同一路 source 的 final transcript 到达
- **THEN** 对话区用 final 内容稳定替换最近对应的 partial，而不是再插入一条重复的新消息

### Requirement: Show accurate chain-state notices in the live conversation panel
实时对话区在没有可见字幕或链路出现异常时 MUST 展示准确的链路状态提示。状态提示 MUST 能区分未绑定桌面端、桌面端未送音、后端仍在接收处理中、provider 返回延迟和前端订阅异常，而不是一律提示“尚未采集到有效音频”。

#### Scenario: Desktop companion is bound but silent
- **WHEN** 当前面试已经完成机器码绑定，但某一路 source 在诊断窗口内没有送入有效音频
- **THEN** 实时对话区提示该路 source 当前未送音，并保留已绑定状态

#### Scenario: Provider is processing but no transcript yet
- **WHEN** 后端已经确认接收到音频并送入 provider，但 partial 尚未返回
- **THEN** 实时对话区提示识别处理中，而不是误导用户去重新绑定机器码

#### Scenario: Frontend loses the subscription
- **WHEN** 后端仍在持续发布 transcript 事件但当前页面订阅异常中断
- **THEN** 实时对话区提示页面订阅异常或延迟，而不是把问题归结为麦克风或电脑输出
