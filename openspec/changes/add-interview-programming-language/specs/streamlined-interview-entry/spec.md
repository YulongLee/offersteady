## ADDED Requirements

### Requirement: Preparation SHALL present and restore an optional programming preference
准备页 SHALL 展示“需要编程”开关且默认关闭；开启后 SHALL 展示 Python、Java、C++、JavaScript、TypeScript 和 Go 的语言选择器并默认 Python。控件 MUST 使用服务端会话值作为权威状态，保存成功后可在刷新和跨设备重新进入时恢复；有效默认值 MUST NOT 增加新的开始面试门禁。

#### Scenario: User enables programming
- **WHEN** 用户在准备页开启“需要编程”
- **THEN** 页面展示语言选择器、默认选中 Python 并将完整配置保存到服务端

#### Scenario: User disables programming
- **WHEN** 用户关闭“需要编程”
- **THEN** 页面隐藏语言选择器并清除服务端编程语言值

#### Scenario: Saved preference is restored
- **WHEN** 用户已选择 C++ 后刷新准备页或从另一设备继续准备
- **THEN** 页面恢复开启状态并选中 C++

#### Scenario: Programming remains optional
- **WHEN** 用户保持“需要编程”关闭且其他现有准备条件均已完成
- **THEN** 系统允许开始面试且不要求额外确认编程配置
