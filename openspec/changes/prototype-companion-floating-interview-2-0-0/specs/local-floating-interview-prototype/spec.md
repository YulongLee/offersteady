## ADDED Requirements

### Requirement: Open an isolated floating interview window

本地助手 2.0.0 MUST 保留原主窗口及操作，并通过托盘菜单打开单个可移动和缩放的浮窗。

#### Scenario: User opens the window twice
- **WHEN** 用户重复选择「桌面浮窗」
- **THEN** 助手聚焦已有窗口并保留当前透明度

#### Scenario: User switches to another window
- **WHEN** 浮窗开启且用户点击其他普通窗口
- **THEN** 浮窗继续置顶

#### Scenario: User adjusts transparency
- **WHEN** 用户打开新的浮窗并调节透明度
- **THEN** 默认透明度为 0%，滑块可在 0% 至 60% 之间调节

#### Scenario: User resizes the window
- **WHEN** 用户调整窗口尺寸
- **THEN** 官网视图调整到可用窗口区域，保留官网的响应式行为

#### Scenario: User temporarily hides the Mac floating window
- **WHEN** 用户点浮窗「收起」，随后从菜单选「桌面浮窗」
- **THEN** 助手先隐藏窗口，再恢复同一个页面、窗口位置和透明度

### Requirement: Connect to the existing CN web app

测试包 MUST 在同一浮窗加载国服现有登录和面试页面。官网视图 MUST 具有独立会话和同源导航限制，且不暴露桌面原生接口。

#### Scenario: User opens the floating workspace
- **WHEN** 用户从桌面菜单打开浮窗
- **THEN** 窗口进入受保护的面试入口，未登录时由官网显示登录，登录后继续准备面试

#### Scenario: Page load fails
- **WHEN** 官网连接失败
- **THEN** 浮窗保留本地控制并提供重试

#### Scenario: External page is requested
- **WHEN** 官网视图尝试跳转非授权站点
- **THEN** 阻止导航或弹窗

#### Scenario: User closes and reopens the window
- **WHEN** 用户关闭后在同一助手进程内重开
- **THEN** 旧网页实例被释放，新页面可以使用本次进程的独立登录会话

### Requirement: Report capture protection accurately

测试浮窗 MUST 按平台显示捕获保护范围。

#### Scenario: User opens the Windows preview
- **WHEN** Windows 显示浮窗
- **THEN** 窗口申请系统捕获保护，界面提示接收端待验证

#### Scenario: User opens the Mac preview
- **WHEN** macOS 本地测试版打开主窗口或桌面浮窗
- **THEN** 助手在窗口显示前请求系统捕获保护。浮窗标明请求状态，提示以会议接收端为准

#### Scenario: User adjusts opacity while capture protection is active
- **WHEN** macOS 用户调整桌面浮窗透明度
- **THEN** 助手保留浮窗本地可见性并重新请求捕获保护

### Requirement: Connect the current companion without manual code entry

测试浮窗 MUST 隐藏面试准备页的机器码输入，复用现有国服流程连接当前助手。

#### Scenario: Preparation form is ready to bind
- **WHEN** 浮窗内打开受信任站点的准备页，官网允许连接且本场尚未绑定
- **THEN** 浮窗自动连接当前助手一次，保留官网的连接结果与失败后的手动重试

#### Scenario: Existing binding or active session conflict
- **WHEN** 本场已有设备绑定或官网要求先处理正在进行的会话
- **THEN** 浮窗保留原绑定和官网的会话冲突确认

### Requirement: Preserve macOS audio permission identity

Mac 2.0.0 候选包 MUST 沿用国服正式助手的签名身份及系统权限要求，保留主助手的麦克风、电脑输出和屏幕采集流程。候选包 MUST 通过 App 与 DMG 的签名、公证及授权声明校验。

#### Scenario: User launches the release candidate for testing
- **WHEN** 用户退出旧助手后，从独立目录打开 2.0.0 候选包
- **THEN** macOS 可按与正式助手相同的签名要求识别应用，主助手按系统已有授权状态执行采集，测试数据存于独立目录

### Requirement: Exclude the floating window from companion screenshots

Mac 2.0.0 测试包 MUST 从原有屏幕预览、快捷键截图和截图回答图片中排除助手应用的全部窗口。

#### Scenario: Companion captures a screen while the overlay is visible
- **WHEN** 用户直接使用助手预览、快捷键或截图回答
- **THEN** 助手对所选显示器进行单次过滤截屏，截图显示助手窗口下方的内容，浮窗仍显示在用户桌面

#### Scenario: Companion cannot reliably exclude the overlay
- **WHEN** 截图时无法确认助手应用身份或无法取得过滤画面
- **THEN** 本次截屏报错，不使用未经过滤的图片

### Requirement: Keep the filtered view inside the original preview

Mac 2.0.0 MUST 在原有「预览」中展示助手过滤后的画面，并移除独立的「共享专用画面」入口。

#### Scenario: User opens the companion menu and previews a display
- **WHEN** 用户打开菜单或点击主助手的「预览」
- **THEN** 菜单没有独立共享入口，助手在原预览界面显示过滤后的图片
