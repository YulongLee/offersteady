## MODIFIED Requirements

### Requirement: Confirm the material list and desktop connection before starting
系统 MUST 在开始面试前保存用户明确确认的本场资料清单，包括空清单，并 MUST 由用户选择“一键连接上次设备”或“输入机器码”完成本场设备连接。开始条件 SHALL 由资料清单确认状态和本场设备 binding 组成；历史面试 binding 不得直接满足本场开始条件。

#### Scenario: User confirms materials and connects the last device
- **WHEN** 用户确认本场资料并一键连接当前账号最近的在线设备
- **THEN** 系统保存本场资料版本、创建本场新 binding 并允许开始面试

#### Scenario: User confirms materials and enters a machine code
- **WHEN** 用户确认本场资料并输入有效机器码完成连接
- **THEN** 系统保存本场资料版本、创建本场新 binding 并允许开始面试

#### Scenario: Material list is not confirmed
- **WHEN** 用户修改了资料选择但尚未保存确认
- **THEN** 系统不允许开始面试，并说明需要确认本场资料

#### Scenario: Device is not explicitly connected for this interview
- **WHEN** 当前面试没有本场 `bound` 设备记录，即使账号历史面试使用过设备
- **THEN** 系统不允许开始面试，并要求用户选择上次设备或输入机器码
