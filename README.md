> 2026-11-04 05:40:36（北京时间）国际服已完成[实时共享阻塞优化](docs/releases/global-realtime-blocking-20261104.1.md)：仅Backend，307输入/295原字节保持，223完整Schema/379配置/46依赖保持，Web/助手1.3.6/worker及国服不变。两服当前公开运行快照与开发代码保存为[release-20261104.1](releases/20261104.1/README.md)，后续从该版本继续优化。当前来源分别见[国服](docs/current-cn-baseline.md)和[国际服](docs/current-global-baseline.md)。以下未提交表述均为各轮历史记录。

> 2026-11-04 04:25:57（北京时间）已完成[国服固定绑定查询修复发布](docs/releases/cn-pinned-binding-20261104.1.md)：仅Backend三文件，实际237输入/234保持，Web/助手1.3.6/Global/worker及模型/收费不变，池关闭。空闲自然连接状态159条P95约44ms；切换前4秒10次502已恢复，验收后未新增。未提交/推送Git。

> 此前国服于2026-11-04 03:33完成[实时共享阻塞优化发布](docs/releases/cn-realtime-shared-20261104.1.md)：仅Backend十二文件增量，实际237输入，保留Web、助手1.3.6、Global、worker及模型/收费，池关闭；独立验收通过。17次代理502集中于启动后前4秒，验收后未新增。最近Git封版仍为release-20261102.1，本轮未提交/推送。

> 此前国服于2026-11-03完成[设备状态上报优化](docs/releases/cn-device-status-20261103.1.md)，仅Backend四文件增量，保留SEO、此前状态/模拟面试优化和助手1.3.6下载清单，连接池关闭；Web、worker及国际服未更新。实际组件以[当前国服基线](docs/current-cn-baseline.md)为准。最近Git封版仍为[release-20261102.1](releases/20261102.1/README.md)，本次线上增量尚未提交/推送Git，本地未发布笔试配套未混入。

# OfferSteady

> 本轮[本地开发与自测记录](docs/releases/cn-device-status-local-20261102.1.md)已保留，2026-11-03国服发布结果见上方记录。

> 2026-11-03新增[国服实时共享阻塞优化本地候选](docs/releases/cn-realtime-shared-local-20261103.1.md)：本地完整回归956通过、1项Global专属跳过；已于2026-11-04按授权发布，真实结果见上方生产记录。

OfferSteady 是一个面向求职者的 AI 面试辅助产品，目前处于产品原型与需求验证阶段。

项目采用 OpenSpec 驱动开发：先明确用户目标、边界和验收标准，再进行技术设计与代码实现。Codex 的长期工作规则记录在 [`AGENTS.md`](./AGENTS.md)，正式功能规范和变更放在 [`openspec/`](./openspec/) 中。

## 当前阶段

- 阶段：产品定义与原型设计
- 当前变更：[`define-interview-assistant-mvp`](./openspec/changes/define-interview-assistant-mvp/)
- 暂未确定：客户端形态、前端框架、后端语言、AI 服务提供方

## 从这里开始

1. 阅读 [`docs/product-vision.md`](./docs/product-vision.md)。
2. 审阅当前变更的 [`proposal.md`](./openspec/changes/define-interview-assistant-mvp/proposal.md)、能力 Specs 和 [`design.md`](./openspec/changes/define-interview-assistant-mvp/design.md)。
3. 解决设计文档中的开放问题，确认 MVP 范围。
4. 确认后使用 `/opsx:apply` 按 [`tasks.md`](./openspec/changes/define-interview-assistant-mvp/tasks.md) 实现。

## 目录说明

```text
docs/         长期有效的产品与架构知识
openspec/     已确认的能力规范和正在进行的变更
specs/        迁移前的手工 Spec，仅作历史参考
design/       原型链接、设计稿和设计系统说明
apps/web      React + TypeScript + Vite 的当前 Web 原型与 MVP 展示层
apps/backend  FastAPI 的 MVP 第一阶段服务端基础工程
apps/api      TypeScript 原型服务参考，不再作为正式后端主线
packages/     后续共享模块
ai/           Prompt、评测集和脱敏样本
tests/        跨应用的集成测试与端到端测试
```

## 当前工程基线

- Web 展示层：`React + TypeScript + Vite`
- 服务端基础工程：`FastAPI`
- 数据与部署底座：`PostgreSQL + pgvector + Aliyun OSS + Docker + Nginx`
- 前端数据访问：产品运行时统一读取 Backend API；测试数据仅允许放在 test-only builders / mocks 中
- 桌面伴随程序：后续阶段接入，不在当前第一阶段实现

补充工程文档：

- [`docs/engineering-foundation.md`](./docs/engineering-foundation.md)
- [`docs/environment-variables.md`](./docs/environment-variables.md)
- [`docs/local-web-access.md`](./docs/local-web-access.md)
- [`infra/README.md`](./infra/README.md)

## 本地运行

```bash
npm run dev:web
npm run dev:backend
```

本地 Web 页面默认会请求 `VITE_API_BASE_URL` 指向的后端，例如 `http://127.0.0.1:8000`。如果后端未启动或核心聚合状态接口异常，前端会显示真实错误状态，不再回退到本地演示数据。

若本地网页访问异常，先运行：

```bash
npm run doctor:web
```

它会区分是本地服务未启动、访问地址错误，还是页面本身异常。

## Spec 工作流

```text
explore -> propose -> 审阅并确认 -> apply -> verify -> archive
```

没有明确验收标准的功能不进入实现阶段。使用 `openspec validate <change> --strict` 校验变更；任何导致行为变化的需求修改，应先更新对应 OpenSpec 变更。
