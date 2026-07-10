## ADDED Requirements

### Requirement: Desktop interview workspace
系统 SHALL 在宽屏设备上提供包含资料状态、当前问题、实时回答、问题历史和会话控制的桌面工作区，并 MUST 让实时回答保持主要视觉层级。

#### Scenario: Desktop workspace opens
- **WHEN** 用户在宽度不小于 1200 像素的视口打开一场面试会话
- **THEN** 系统展示三栏工作区和固定可达的会话控制区

#### Scenario: Supporting panel collapses
- **WHEN** 用户折叠资料栏或历史栏
- **THEN** 实时回答区域扩展且当前问题和会话控制保持可见

### Requirement: Mobile companion workspace
系统 SHALL 在手机视口提供适合单手操作的伴随页面，优先展示连接状态、当前问题、回答提纲、会话控制和拍照入口。

#### Scenario: Mobile companion opens
- **WHEN** 用户在宽度小于 768 像素的视口加入面试会话
- **THEN** 系统展示单栏现场页面、底部导航和可触达的主要会话操作

#### Scenario: User requests full answer
- **WHEN** 手机端用户点击展开完整回答
- **THEN** 系统在不离开当前会话的情况下展示完整回答并提供返回提纲的入口

### Requirement: Responsive intermediate layout
系统 MUST 在 768 至 1199 像素宽度之间保持完整核心流程，并将次要区域转换为抽屉或可折叠面板。

#### Scenario: Viewport crosses a breakpoint
- **WHEN** 视口尺寸跨越响应式断点
- **THEN** 系统重新排布内容而不丢失当前问题、回答、滚动内容或会话状态

### Requirement: Present synchronized state consistently
所有布局 MUST 使用一致的状态名称和含义展示会话、问题、回答生成、资料和设备连接状态。

#### Scenario: Answer starts generating
- **WHEN** 任一设备收到回答生成中的已确认状态
- **THEN** 当前布局展示对应问题、生成指示和已到达的增量内容

#### Scenario: Device goes offline
- **WHEN** 当前设备失去同步连接
- **THEN** 界面明确显示离线状态且不继续宣称内容正在同步

### Requirement: Accessible and low-distraction controls
系统 SHALL 为主要操作提供键盘可达、清晰焦点、文字标签和足够触控面积，并 MUST 不只依赖颜色表达状态。

#### Scenario: Keyboard navigation on desktop
- **WHEN** 用户仅使用键盘操作桌面工作区
- **THEN** 用户可以按可预测顺序访问资料、回答、历史和会话控制

#### Scenario: Touch operation on mobile
- **WHEN** 用户在手机端操作会话控制
- **THEN** 主要触控目标具有至少 44×44 CSS 像素的可操作区域

### Requirement: Protect sensitive content in the interface
系统 MUST 避免在系统通知、页面标题或未授权设备上暴露完整简历、问题或回答内容。

#### Scenario: Unpaired device opens session link
- **WHEN** 未授权设备尝试打开一场进行中的会话
- **THEN** 系统只展示身份验证或配对界面，不展示任何面试内容
