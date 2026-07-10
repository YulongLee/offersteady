# OfferSteady

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
