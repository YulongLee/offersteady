# cn-core-seo-20260908.1 国服生产发布结果

发布时间：2026-09-08 01:29:07 +08:00。
最终线上 Web 版本：`cn-core-seo-20260908.1`。
生产地址：https://mianshiwen.cn/ 。

## 范围和发布方式

- 仅发布本轮批准的国服四页 SEO/GEO 内容及必要构建产物；不包含主工作区其他改动，不修改海外版本。
- 发布前将生产源码下载到隔离目录，与国服工作树逐项比较。App运行代码仅首屏定义和三项FAQ增量；其余运行时源码、config/protocol与生产一致。未上传不相关测试差异或后端文件。
- 沿用此前国服Web发布方式：旧hash资源保留、先补资源、逐文件原子替换HTML、Nginx语法验证和平滑重载。没有运行全栈compose up，没有重启后端、数据库或管理平台。
- 发布门禁：实时桌面传输、队列worker、排队帧、回答执行/等待、截图执行全部为0；30分钟内活动的live面试为0。有1条无近期活动的历史live记录，未关闭或修改。
- 8个原有compose容器ID前后完全相同。66个原有hash JS/CSS保留，缺失旧资源问题未重现。
- 临时候选检查容器已删除；没有删除业务数据。HTML、配置和源码备份仍保留，可回滚。
- 后端版本保持 `cn-quick-answer-film-20260907.1`。

## 价格门禁

发布前多次实际执行 `node apps/web/scripts/verify-pricing-live.mjs`，发布紧前检查通过：10个上架商品、生产目录版本16、渲染价格与权益一致，快照未超24小时。无需重建，没有发布失效快照。
发布后对生产 `/pricing` 原始HTML再次与实时目录逐项渲染核对，两种UA均通过。

目录指纹：`b4766ec3fab1a60df7ed290ee6900da3501a3f543741b6b695aebd52b7ea1287`。
该功能仍是构建时快照；今后调价/上下架需要同步重建发布Web。

## 生产原始HTTP验证

使用普通UA及 `Baiduspider/2.0` 请求真实生产URL，不依赖JS执行。每页的Title、H1、Description、Canonical、main正文和全部锚链接均与验收构建精确比较；同时验证JSON-LD的CSP hash和无noindex。

| URL | 普通 UA | Baiduspider | 验证 |
|---|---:|---:|---|
| / | 200 | 200 | 产品定义、Title/H1、问答与内链一致 |
| /pricing | 200 | 200 | 独立价格正文，10项真实金额/权益，实时价格校验通过 |
| /features/realtime-interview | 200 | 200 | 六步流程与回答建议正文一致 |
| /features/ai-interview-assistant | 200 | 200 | 技术场景与7个专题链接一致 |
| /sitemap.xml | 200 | 200 | 与验收XML逐字节一致，仍30URL |

全部30个sitemap URL在两种UA下均200（60次页面检查），各自metadata、正文、canonical及链接与构建一致。四页28个唯一站内链接HEAD均200。

[完整60行生产验证记录](../audits/cn-core-seo-20260908/production/production-verification.json)。
同目录保留两种UA的30页原始HTML及sitemap XML。

## 现有业务只读冒烟

| 检查 | 结果 |
|---|---|
| /login、/app、/app/billing、/app/interviews/new、/app/devices | 均200，现有入口可访问 |
| /healthz | ok，后端版本不变 |
| /api/v1/billing/status | 200 |
| 公共配置中的支付渠道 | alipay、wechat仍可用 |
| /download | 200 |
| macOS arm64、macOS x64、Windows x64安装包 | 实际GET Range 0-0均206、正确文件类型和文件长度 |
| 前一版本 main-D8GtcuCK.js及更早 main-DLJpquzR.js | 均200且返回JS，不是首页shell |
| 8个原有服务容器 | ID完全一致，没有重建 |

下载API本身不支持HEAD（405且Allow: GET），因此改用真实GET Range验证，三个文件均通过；未全量下载大安装包。
没有为测试发送验证码、创建订单、发起真实支付或创建面试。上述为只读路由/服务冒烟及容器一致性，不冒称已经做过真实付费与面试端到端交易测试。

## 技术债

开发阶段53个测试文件、387项测试、build、typecheck、SEO源码/原始HTML与移动端验证已通过。
已有JS体积预算仍超标：总1,364,681B、入口444,227B。本次按照用户明确授权记录为技术债，没有放宽阈值，也没有重构业务Bundle。

## 可追溯性和回滚

- 本地国服源码：`/private/tmp/offersteady-cn-release-20260907.DTlvCc`
- 生产源码：`/opt/offersteady/releases/20260907-cn-home-downloads-1`（仅精确sources.tgz清单同步）
- 发布与备份目录：`/tmp/cn-core-seo-release-20260908/`
- 保留资源审计：`/tmp/offersteady-retained-assets.fnIG5Z/`
- 镜像标签：`compose-web:cn-core-seo-20260908.1` 和 `compose-web:latest`
- 镜像ID：`sha256:1b28c2f8a63bb36b94e7939e9811b0072c750d2f8657b4a489bc4fbaa8ed0777`
- 前一镜像：`compose-web:cn-indexing-20260908.1`
- 回滚方案：恢复backup中9个HTML/XML/manifest文件、default.conf和source，nginx -t后平滑reload，将latest恢复前一镜像。已添加新hash资源可保留，不需要删除。无需数据库回滚。
- 验证脚本：`apps/web/scripts/verify-core-seo-production.mjs`
- [本轮修改前后对照](../audits/cn-core-seo-20260908/REPORT.md)

收录与排名需要后续观察百度平台，以上技术检查不等于百度已完成收录。
