## ADDED Requirements

### Requirement: Use interview-oriented wording for the explicit start action
准备页与已绑定桌面伴随程序的主要启动操作 SHALL 使用“开始面试”，不得把面向用户的主操作命名为“开始收音”。文案调整 MUST NOT 改变明确授权边界：未开始时不得发送音频，手动模式开始面试不得隐式启用音频，音频模式仍需已授予对应系统权限并持续显示采集状态。

#### Scenario: Bound companion is ready
- **WHEN** 桌面设备已绑定、所选音频来源已授权并通过测试
- **THEN** 主按钮显示“开始面试”，点击后才开始发送所选音频并同步会话进行中状态

#### Scenario: User starts in manual mode
- **WHEN** 用户未启用音频来源而在 Web 点击“开始面试”
- **THEN** 系统进入面试工作台但不请求或启动麦克风与系统音频采集

#### Scenario: Permission is missing
- **WHEN** 用户选择音频模式但所需系统权限尚未授予
- **THEN** 系统不因按钮改名而绕过权限，并引导用户完成对应来源授权后再开始

#### Scenario: Interview is already running
- **WHEN** 一个已授权客户端已经成功开始当前会话
- **THEN** 其他 Web 或桌面客户端同步进行中状态且不继续显示可重复执行的“开始面试”主操作
