## ADDED Requirements

### Requirement: Public entry explains the product boundary
系统 SHALL 提供无需登录即可访问的公开入口，说明网页主产品、Mac 收音伴随程序、AI 建议属性和敏感数据处理边界。

#### Scenario: First-time visitor opens the product
- **WHEN** 未登录用户访问公开首页
- **THEN** 系统展示核心使用流程、平台分工、隐私说明和明确的进入应用操作

### Requirement: Protected application routes
系统 MUST 要求用户通过允许的身份方式进入受保护应用路由，并 MUST 不向未授权访问者渲染面试资料或回答内容。

#### Scenario: Unauthorized session link is opened
- **WHEN** 未授权用户打开受保护的实时面试链接
- **THEN** 系统显示身份入口并隐藏该会话的标题、问题、回答和资料

### Requirement: Consistent application navigation
系统 SHALL 在登录后提供面试首页、资料库、设备和设置的稳定导航，并 SHALL 在面试准备与实时会话中保留明确的返回路径。

#### Scenario: User navigates between product areas
- **WHEN** 用户从面试首页进入设备页面后返回
- **THEN** 系统恢复原页面位置和未完成的安全表单状态

### Requirement: Action-oriented application home
系统 SHALL 在应用首页优先展示进行中会话、创建面试、最近记录和资料就绪摘要，而不是要求用户理解空白数据面板。

#### Scenario: New user has no interviews
- **WHEN** 已登录用户没有面试或资料
- **THEN** 系统展示创建第一场面试的引导、流程说明和可跳过的演示入口

#### Scenario: Active interview exists
- **WHEN** 用户存在一场未结束的面试
- **THEN** 系统在首要位置展示继续面试操作及其同步和设备状态

### Requirement: Responsive and accessible shell
应用外壳 MUST 在桌面、平板和手机宽度下保持核心导航可达，并 MUST 支持键盘焦点、文字状态和至少 44×44 CSS 像素的主要触控目标。

#### Scenario: Mobile navigation opens
- **WHEN** 用户在小于 768 像素的视口进入登录后应用
- **THEN** 系统使用适合单手操作的导航且不遮挡主要页面操作
