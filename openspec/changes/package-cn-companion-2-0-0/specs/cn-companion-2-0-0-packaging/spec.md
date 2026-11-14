## ADDED Requirements

### Requirement: Prepare consistent platform candidates

系统 MUST 从同一冻结国服 2.0.0 候选准备 Apple Silicon、Intel 和 Windows x64 安装产物，并记录各自来源、校验值与验证状态。

#### Scenario: A platform build is unavailable
- **WHEN** 某平台构建或必要验证失败
- **THEN** 该平台标为未完成并记录原因，不将其他平台的测试产物冒充其正式产物

### Requirement: Preserve existing companion identity and behavior

正式模式 MUST 保留国服正式设备身份、稳定数据目录、原功能及平台权限流程，浮窗保持现有测试版交互。身份迁移测试 MUST 使用合成数据。

#### Scenario: Existing user upgrades
- **WHEN** 带有合成既存正式身份的设备升级至正式候选
- **THEN** 继续使用已有身份且不覆盖既存凭证或转入测试版身份目录

#### Scenario: User opens floating window
- **WHEN** 用户在主程序菜单选择桌面浮窗
- **THEN** 原主界面和既有功能保留，浮窗可打开、置顶、拖动、缩放并调整透明度

### Requirement: Report signing and test status honestly

Mac 正式候选 MUST 完成 Developer ID、App 和 DMG 公证与验证；Windows MUST 如实记录代码签名与实际设备验证状态。

#### Scenario: Notarization fails or is unavailable
- **WHEN** Mac App 或 DMG 公证、签名、staple 或 Gatekeeper 校验未通过
- **THEN** 该包不标为正式发行候选并记录实际结果

#### Scenario: Windows device test is not performed
- **WHEN** 没有真实 Windows 设备的验收结果
- **THEN** 记录未实测，不以静态包检查替代实机验收

### Requirement: Report capture protection limits

助手 MUST 将第三方共享保护的实际状态与助手自身预览过滤区分；不能宣称对所有会议软件有效。

#### Scenario: User shares or records using Zoom
- **WHEN** 当前用户已观察到 Zoom 共享和录制画面显示浮窗
- **THEN** 发布材料保留该限制，不将系统保护请求成功表述为 Zoom 隐藏成功

#### Scenario: Companion captures its own preview
- **WHEN** Mac 助手取得经过滤的预览或截图
- **THEN** 排除助手窗口，无法确认过滤时不得回退到未过滤画面

### Requirement: Keep packaging local

本变更 MUST 只生成和验证本地候选，不对线上服务、下载入口或远程分发对象做修改。

#### Scenario: Candidate is ready for review
- **WHEN** 本地封装和可执行检查完成
- **THEN** 输出文件路径、验证证据和未完成事项，不执行部署或上传
