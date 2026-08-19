# 面试稳 SEO / GEO 执行记录

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
