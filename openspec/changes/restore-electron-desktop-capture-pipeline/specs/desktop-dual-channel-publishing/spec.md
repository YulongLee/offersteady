## ADDED Requirements

### Requirement: Desktop publishes two role-scoped channels
一个 live 桌面 publisher SHALL 分别发布 `microphone` 和 `system` 音频通道，后端 MUST 将其映射为 `candidate` 和 `interviewer`。

#### Scenario: Candidate speaks
- **WHEN** 麦克风适配器产生满足语音门限的音频段
- **THEN** publisher 将该段作为 `microphone` 通道发送，网页最终显示候选人角色转写

#### Scenario: Interviewer audio plays on the computer
- **WHEN** system adapter 产生满足语音门限的电脑输出音频段
- **THEN** publisher 将该段作为 `system` 通道发送，网页最终显示面试官角色转写

### Requirement: Publishing health reflects end-to-end evidence
助手 SHALL 分别跟踪每个通道的媒体轨道、电平、采集帧、发送帧、服务端确认和 ASR 状态，且 MUST NOT 仅根据本地电平判断实时对话已拉通。

#### Scenario: Local meter moves but server receives no frames
- **WHEN** 电脑输出存在非零电平但服务端未确认任何 system frame
- **THEN** 助手显示电脑输出发布异常或正在重连，而不是显示面试官通道可用

#### Scenario: Server accepts both channels
- **WHEN** 服务端分别确认 microphone 和 system 帧并产生对应 ASR 事件
- **THEN** 助手显示双通道实时发布可用

### Requirement: Exactly one publisher is authoritative per session and source
服务端 MUST 保持同一面试和同一音频来源最多一个权威 active publisher，新 publisher 建立时 SHALL 关闭并清理旧 publisher。

#### Scenario: Desktop reconnects to the same live session
- **WHEN** 同一设备为相同 session 和 source 创建新的 publisher
- **THEN** 服务端关闭旧 publisher，仅接受新 publisher 的后续帧

### Requirement: Audio delivery is bounded and recoverable
桌面 publisher MUST 使用有界缓冲和串行发送，临时网络或 ASR 错误 SHALL 可恢复且不得形成无限积压。

#### Scenario: Network is temporarily unavailable
- **WHEN** 音频发送短暂失败后网络恢复
- **THEN** publisher 在有界退避后恢复发送，并丢弃超过缓冲上限的旧 interim 音频

#### Scenario: ASR rejects one frame
- **WHEN** 一个有效 publisher 的单帧 ASR 处理失败
- **THEN** 服务端将通道标记为 degraded，并允许后续帧恢复该 publisher
