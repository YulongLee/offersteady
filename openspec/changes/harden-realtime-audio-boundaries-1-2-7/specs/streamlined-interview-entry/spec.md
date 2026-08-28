## MODIFIED Requirements

### Requirement: Confirm the material list without a redundant data-purpose checkbox
系统 MUST 在开始面试前保存用户明确确认的本场资料清单，包括空清单，但 MUST NOT 再要求勾选“我已了解本场数据用途”或同义的通用复选框。开始条件 SHALL 由资料清单确认状态和至少一种可用问题输入方式组成。音频辅助方式 SHALL 在绑定伴随程序后自动检查设备在线、权限与回调并预热识别服务，但 MUST NOT 要求用户在准备页播放测试音或先说话；开始后 SHALL 将已准备状态原子地转入实时链路。手动输入 SHALL 继续不依赖音频权限。

#### Scenario: User confirms selected materials
- **WHEN** 用户选择资料并点击确认本场资料
- **THEN** 系统保存会话级选择版本，并在所选问题输入方式可用时启用“开始面试”

#### Scenario: User confirms an empty list
- **WHEN** 用户明确确认简历、JD 和知识材料均为空
- **THEN** 系统保存空允许清单并允许继续，不再要求额外勾选通用数据用途确认

#### Scenario: Material list is not confirmed
- **WHEN** 用户修改了选择但尚未保存确认
- **THEN** 系统不允许开始面试，并说明需要确认本场资料而不是提示数据用途复选框

#### Scenario: Preparation has no prior sound
- **WHEN** 伴随程序已绑定且在线，但用户尚未播放声音或对麦克风说话
- **THEN** 系统不显示强制声音验证、不以缺少历史真实信号阻止开始，并继续在后台完成音频与识别服务准备

#### Scenario: Audio path has an explicit failure
- **WHEN** 伴随程序离线、必需权限明确被拒绝或音频回调明确失败
- **THEN** 系统指出对应故障，不把失败状态误报为就绪

#### Scenario: Verified audio path enters live
- **WHEN** 所有必需来源和识别服务均就绪且用户开始面试
- **THEN** 系统复用已验证的媒体来源和隐私安全校准状态，不重新打开健康设备或冷启动本地检测器

#### Scenario: Manual input remains available
- **WHEN** 用户选择不使用音频采集的手动输入方式且资料清单已确认
- **THEN** 系统允许进入实时工作台且不要求麦克风或电脑输出权限与校准
