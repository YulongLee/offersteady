## ADDED Requirements

### Requirement: Public homepage exposes the Baidu verification marker
系统 MUST 在公开首页原始 HTML 的 `<head>` 中提供百度搜索资源平台指定的站点验证 meta 标记，并在生产构建与后续发布中保持准确。

#### Scenario: Baidu fetches the public homepage
- **WHEN** 百度验证服务请求公开首页 HTML
- **THEN** 响应的 `<head>` 包含且仅包含一个名称为 `baidu-site-verification`、内容为已批准验证码的 meta 标记

#### Scenario: Web production bundle is built
- **WHEN** Web 应用执行生产构建
- **THEN** 构建产物首页继续包含准确的百度验证标记

### Requirement: Verification does not add tracking or alter product behavior
站点验证变更 MUST 仅增加静态 meta 标记，不得引入脚本、网络请求、Cookie 或业务行为变化。

#### Scenario: User loads the site after verification is added
- **WHEN** 用户访问首页或应用页面
- **THEN** 页面交互、API、实时面试、桌面助手与隐私行为保持不变
