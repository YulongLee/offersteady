## ADDED Requirements

### Requirement: Preparation SHALL present and restore the interview language
准备页 SHALL 展示单选式“面试语言”设置，默认选中“中文面试”，并提供“English Interview”。该设置 MUST 使用服务端会话值作为权威状态，修改成功后立即持久化；页面刷新、跨设备重新进入或从首页继续准备时 MUST 恢复已保存值，而不是重新套用中文默认值。

#### Scenario: User opens a new preparation page
- **WHEN** 新会话未显式选择语言且用户进入准备页
- **THEN** 页面选中“中文面试”，并说明该选择决定识别与 AI 回答语言

#### Scenario: User chooses English and refreshes
- **WHEN** 用户在 `preparing` 状态选择“English Interview”且服务端保存成功后刷新页面
- **THEN** 页面仍选中“English Interview”，不会因本地状态重建而恢复为中文

#### Scenario: Language save fails
- **WHEN** 用户切换语言但持久化请求失败
- **THEN** 页面恢复服务端已确认值、展示可重试错误，并禁止把未保存的选择当作开始后的链路配置

#### Scenario: User returns to a live interview
- **WHEN** 用户重新进入已经开始的面试
- **THEN** 页面和实时工作台可显示已锁定语言，但不提供修改入口

### Requirement: Preparation start SHALL use the persisted language without adding a new readiness blocker
语言拥有有效默认值，因此准备页的资料确认和设备绑定规则 MUST 保持不变，语言选择 MUST NOT 增加一个需要额外确认的阻塞步骤。开始请求 SHALL 使用服务端已持久化语言；开始与语言更新并发时，系统 MUST 以原子状态约束避免页面显示一种语言而运行另一种语言。

#### Scenario: User keeps the default Chinese selection
- **WHEN** 用户不操作语言选项且已满足现有资料和设备条件
- **THEN** “开始面试”按原规则可用，并以 `zh-CN` 启动

#### Scenario: Saved English selection starts
- **WHEN** 用户已成功保存 `en-US` 且满足现有资料和设备条件
- **THEN** 会话进入 `live` 后所有下游链路读取同一个 `en-US` 值
