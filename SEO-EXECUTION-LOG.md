# 面试稳 SEO / GEO 执行记录

## 2026-08-19：商业决策页与高意图内容权威

### 已实施

- 5 个静态商业决策页：积分与会员、电脑助手下载、安全说明、关于产品、联系支持。
- 4 个高意图指南：macOS 权限、飞书音频、腾讯会议音频、STAR 回答结构。
- 两个既有指南升级为 Article，补充组织审核者、发布日期、更新日期、直接答案和来源范围。
- sitemap 扩展到 17 个 URL；robots 显式允许 GPTBot、OAI-SearchBot、ChatGPT-User、ClaudeBot 与 PerplexityBot。
- `llms.txt`、`llms-full.txt`、`public-facts.json` 增加商业页面、维护指南、动态事实和实体边界。
- 首页社交分享标题缩短；公开导航、Nginx 路由、CSP 哈希和构建后校验同步更新。

### 验证结果

- SEO/GEO 源码检查：17 个公开页面通过。
- Web 测试：38 个文件、263 条用例通过；所有工作区 TypeScript 检查通过。
- 生产构建与构建后检查通过：入口 JS 394,838 bytes；全部 JS 1,288,685 bytes；CSS 95,023 bytes。
- 代表性 `/pricing` Lighthouse：移动端和桌面端 Performance、Accessibility、Best Practices、SEO 均为 100；移动 LCP 0.903 秒，桌面 LCP 0.251 秒，TBT 0、CLS 0。
- OpenSpec `expand-commercial-seo-geo-conversion --strict` 通过。

### 环境限制

- 通用 schema 校验器不识别合法的顶层 `@graph`，项目校验已逐个解析图节点并验证 context、类型、日期和 CSP 哈希。
- 本机 Docker 守护进程未启动，未执行容器内 `nginx -t`；Nginx 映射、缓存、敏感路由 noindex/no-store 与真实 404 由源码级发布门禁覆盖。
- Search Console、百度、GA4、CrUX 字段指标、排名、流量和转化仍未知。

## 2026-08-19：公开主题集群与 GEO 基础

### 已实施

- 6 个静态专题页与共享轻量样式。
- 首页、使用手册和专题页内部链接网络。
- 8 URL sitemap 与逐页 `lastmod`。
- `llms.txt`、`llms-full.txt`、`public-facts.json`。
- 明确 Nginx 路由、缓存、MIME 类型与 JSON-LD CSP 哈希。
- 品牌图标显示资源从 512px / 248 KiB 优化为 96px / 约 12 KiB；平台图片补齐固定尺寸。
- 源码与构建产物 SEO/GEO 发布门禁。

### 验证结果

- SEO/GEO 源码检查：8 个公开页面通过。
- Web 测试：38 个文件、263 条用例通过。
- TypeScript 与生产构建：通过。
- 构建产物：入口 JS 394,349 bytes；全部 JS 1,288,196 bytes；CSS 95,023 bytes，均在当前回归预算内。
- 本地路由冒烟：11 个公开页面/资源返回 200；未知路径返回 404。
- OpenSpec：`optimize-public-seo-geo-growth --strict` 通过。
- Lighthouse：首页、手册、代表性专题页各运行 3 次并取中位数；详见 `FULL-AUDIT-REPORT.md`。

### 未验证或等待外部权限

- Google Search Console、百度搜索资源平台、GA4、CrUX 字段数据。
- 实际收录、排名、搜索展示、点击率、自然注册和付费转化。
- 备案主体工商全称与首页量化营销数据的统计口径。

这些项目不得由实验室测试或代码推断，需在获得平台权限或业务证据后补录。
