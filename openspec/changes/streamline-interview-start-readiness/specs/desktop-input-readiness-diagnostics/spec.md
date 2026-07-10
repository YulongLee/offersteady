## ADDED Requirements

### Requirement: Local companion owns input readiness diagnostics
下载的本地端软件 SHALL 负责检查麦克风、系统音频、声道来源、问题检测和自动转写能力，并 SHALL 将诊断状态同步给 Web 展示。Web 准备页 MUST NOT 把这些诊断状态作为进入实时面试页的前置条件。

#### Scenario: Companion is not connected before interview start
- **WHEN** 用户已确认本场资料但本地端软件未连接
- **THEN** Web 仍允许进入实时面试页，并展示本地端未连接时自动收音不可用但手动输入和截图回答可用

#### Scenario: Companion reports audio permission issue
- **WHEN** 本地端软件报告麦克风或系统音频权限缺失
- **THEN** Web 展示需要在本地端完成授权的状态，但不得退出实时面试页或阻止用户继续使用手动输入和截图回答

#### Scenario: Companion reports question detection unavailable
- **WHEN** 本地端软件报告声道来源混合、系统音频不可用或问题检测不可用
- **THEN** Web MUST 停止自动确认面试官问题，并提示用户检查本地端来源或改用手动输入

### Requirement: Entering interview does not imply capture authorization
进入实时面试页 SHALL 只表示会话进入可回答状态，不得被解释为用户授权本地端开始收音、截图上传或自动问题检测。本地端和 Web MUST 在实际采集或上传动作发生前分别保留明确授权或确认边界。

#### Scenario: User clicks start interview from preparation
- **WHEN** 用户在资料已确认后点击“开始面试”
- **THEN** 系统进入实时面试页并保持采集状态为未开始，除非本地端已在用户明确授权下开始发送音频

#### Scenario: User later starts capture from companion
- **WHEN** 用户在本地端软件中完成音频授权并开始采集
- **THEN** Web 接收并展示采集状态变化，但自动回答仍只基于本地端发布的有效面试官问题事件触发
