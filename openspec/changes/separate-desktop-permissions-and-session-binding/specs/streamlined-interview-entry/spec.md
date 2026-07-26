## MODIFIED Requirements

### Requirement: Provide one continuation action per active interview
面试首页 SHALL 为每场未结束面试只展示一个名为“继续面试”的主要操作，并 MUST NOT 同时展示“继续准备”和“预览工作台”。系统 MUST 根据服务端会话状态决定目标页面，而不是由用户猜测入口差异。用户进入历史面试准备或实时阶段时，系统 SHALL 提供“一键连接上次设备”和“重新输入机器码”两种设备连接方式。

#### Scenario: Interview is still preparing
- **WHEN** 用户点击一场 `preparing` 面试的“继续面试”
- **THEN** 系统进入该场准备页、恢复已保存的本场资料选择，并提供最近设备复用或机器码连接

#### Scenario: Interview is in progress
- **WHEN** 用户点击一场 `live` 或可恢复面试的“继续面试”
- **THEN** 系统直接进入该场实时工作台，保留当前有效设备 lease；若 lease 已失效则提供最近设备复用或机器码连接

#### Scenario: Dashboard is rendered
- **WHEN** 首页展示一场未结束面试
- **THEN** 该面试卡片不存在第二个“预览工作台”或同义的并行入口

### Requirement: Keep disclosure and permission specific to the sensitive action
准备页 SHALL 在开始操作附近简洁说明已选资料和转录用于生成回答、原始音频默认不保存以及记录可删除。麦克风、系统音频和屏幕录制权限 MUST 由桌面助手在首次使用相应能力时向操作系统申请；Web 只展示助手报告的权限状态，不得再次申请浏览器媒体权限。截图上传仍 MUST 在提交前提供预览和确认。

#### Scenario: Desktop permissions were already granted
- **WHEN** 用户使用同一已授权助手连接新面试或历史面试
- **THEN** Web 仅建立本场设备 lease，不再次触发麦克风、系统音频或屏幕权限请求

#### Scenario: User starts in manual mode
- **WHEN** 用户使用手动输入进入面试且未连接桌面助手
- **THEN** 系统无需取得任何音频权限，手动问答保持可用

#### Scenario: Desktop reports missing permission
- **WHEN** 已连接助手报告麦克风或屏幕录制权限缺失
- **THEN** Web 展示在助手或系统设置中处理的明确提示，不自行请求浏览器权限

#### Scenario: User submits a screenshot
- **WHEN** 用户通过助手获得截图并准备上传图片
- **THEN** 系统在提交前展示预览和确认，取消时不把图片加入会话
