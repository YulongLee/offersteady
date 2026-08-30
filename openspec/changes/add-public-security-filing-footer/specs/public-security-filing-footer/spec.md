## ADDED Requirements

### Requirement: Public homepage displays the public-security filing record
公开首页 SHALL 在页面最底部显著展示公安联网备案号“浙公网安备33010602014812号”，并 MUST 保留现有 ICP 备案号和版权信息。

#### Scenario: Visitor reaches the homepage footer
- **WHEN** 访客滚动到公开首页最底部
- **THEN** 页面展示完整的公安备案号“浙公网安备33010602014812号”
- **AND** 页面仍展示现有 ICP 备案号和版权信息

### Requirement: Public-security filing number opens the official record
公安联网备案号 SHALL 是可访问的外部链接，目标 MUST 包含备案记录代码 `33010602014812`，并 SHALL 使用安全的新窗口外链属性。

#### Scenario: Visitor checks the public-security filing record
- **WHEN** 访客点击“浙公网安备33010602014812号”
- **THEN** 浏览器打开公安机关互联网安全管理平台对应记录的查询地址
- **AND** 链接使用新窗口及安全的外链关系属性

### Requirement: Filing information remains usable on narrow screens
首页法律信息栏 MUST 允许 ICP 与公安备案链接在窄屏下换行，不得造成水平溢出或遮挡。

#### Scenario: Visitor views the footer on a mobile viewport
- **WHEN** 首页在窄屏视口中展示最底部法律信息
- **THEN** 版权、ICP 备案和公安备案信息保持可读且可点击
- **AND** 页面不因备案信息产生水平滚动
