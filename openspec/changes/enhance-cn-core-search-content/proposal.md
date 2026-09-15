## Why

用户希望在已有国服本地新版基础上提高内容、商业表达和 SEO/GEO 质量。2026-09-12 检查确认核心抓取基础存在，但部分功能页停留在概述、下载入口说明落后于首页、机器可读价格指引未同步公开价格页，需要先做可验证的现有页面深化。

## What Changes

- 本地优化既有实时辅助、程序员场景、价格、下载四页，加入自包含问题答案、明确标注的说明示例和适用边界。
- 同步 llms.txt、llms-full.txt、public-facts.json 的价格入口和技术场景定位。
- 改善四页阅读层级、段落导航、窄屏和键盘可用性；保持轻量静态 HTML，不新增运行时 JS。
- 同步实际修改页面的 lastmod 和对应 JSON-LD CSP 精确哈希，增加内容与静态交付回归测试。
- 继续使用隔离候选，保留当前首页设计和既有业务，先本地预览。

## Capabilities

### New Capabilities

- `cn-search-content-quality`: 国服现有核心页的具体内容、真实事实、发现信息一致性与静态交付验收。

### Modified Capabilities

- 无。

## Impact

实现位于 `artifacts/cn-homepage-layout.82qdGV/candidate` 的 `apps/web/public/`、相关测试与候选 `infra/nginx/default.conf`（仅 JSON-LD hash）。不覆盖主工作区未确认改动。

非目标：不部署、不新增 URL、不改 canonical 或 robots 策略、不重构业务 Bundle、不改海外版、后端、登录、支付、套餐金额或模型行为；不创建订单、不接触用户音频或个人资料。示例只用合成教学内容，不虚构评价、竞品数据、性能、排名或审核承诺。
