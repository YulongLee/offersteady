## ADDED Requirements

### Requirement: Main companion window keeps screen imagery hidden
桌面伴随程序 SHALL 在主页面仅显示屏幕来源选择、预览入口和截屏快捷键控制，不得常驻显示所选屏幕的缩略图、视频画面或空预览占位区。

#### Scenario: User opens the companion window
- **WHEN** 用户打开伴随程序且屏幕来源已经可用
- **THEN** 主页面不显示任何屏幕画面
- **AND** 用户仍能选择屏幕并点击“预览”

### Requirement: Manual preview opens an on-demand dialog
桌面伴随程序 SHALL 仅在用户主动点击“预览”时打开屏幕预览弹层，并 SHALL 在异步获取开始时立即显示加载反馈。

#### Scenario: Preview is requested successfully
- **WHEN** 用户点击“预览”且所选屏幕可以捕捉
- **THEN** 系统立即打开预览弹层并展示加载状态
- **AND** 获取完成后在弹层内展示所选屏幕的最新画面

#### Scenario: Preview fails
- **WHEN** 用户点击“预览”但系统权限或捕捉运行时返回错误
- **THEN** 弹层保留打开并展示可理解的失败信息
- **AND** 主页面不新增常驻屏幕画面

#### Scenario: Preview is closed
- **WHEN** 用户关闭屏幕预览弹层
- **THEN** 系统隐藏屏幕画面并停止该次临时预览的媒体流
- **AND** 用户可以再次点击“预览”获取最新画面

### Requirement: Capture tasks do not open the preview dialog
桌面伴随程序 MUST 将手动屏幕预览与正式截屏回答任务分离。

#### Scenario: Screenshot is triggered outside the preview button
- **WHEN** 用户使用截屏快捷键或网页端创建截屏回答任务
- **THEN** 本地助手不得自动打开屏幕预览弹层
- **AND** 既有截屏回答链路继续执行

### Requirement: Capture processing keeps a stable preview control
桌面伴随程序 SHALL 在截屏任务处理期间禁止切换屏幕或再次预览，但预览按钮 SHALL 始终显示“预览”，不得向用户展示“取消当前截屏”。

#### Scenario: Screenshot is being processed
- **WHEN** 当前截屏任务正在处理
- **THEN** 屏幕来源和“预览”按钮临时禁用
- **AND** 按钮文案仍为“预览”
- **AND** 主页面不显示“取消当前截屏”操作
