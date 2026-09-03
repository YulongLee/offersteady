## Why

百度搜索资源平台需要在站点首页 HTML 的 `<head>` 中读取指定验证标记，当前生产首页缺少该标记，因此站点所有权验证无法完成。

## What Changes

- 在 Web 首页 HTML `<head>` 中加入百度提供的 `baidu-site-verification` meta 标记。
- 增加回归检查，确保生产构建保留正确标记且后续版本不会误删。
- 仅发布 Web 静态内容，不修改 Backend、桌面伴随程序、实时面试、计费或用户界面。

## Capabilities

### New Capabilities

- `baidu-site-verification`: 公开首页必须稳定提供百度搜索资源平台要求的站点验证标记。

### Modified Capabilities

无。

## Impact

- Web：`apps/web/index.html` 及对应静态 HTML 回归测试。
- Deployment：仅重新构建和切换 Web 静态容器。
- API、数据、隐私、AI 行为与桌面客户端均不受影响。
