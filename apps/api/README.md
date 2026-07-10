# TypeScript Prototype Service Reference

`apps/api` 当前保留为历史原型服务参考，不再作为 MVP 第一阶段的正式后端主线。

它仍然有价值的地方：

- 保留早期原型中验证过的契约与错误形状
- 为前端交互和共享协议提供回归样本
- 为 FastAPI 迁移阶段提供“行为参考”，帮助确认哪些逻辑只是原型、哪些适合沉淀到共享契约

正式后端基础工程已经迁移到 `apps/backend`。

后续规则：

- 新的 MVP 服务端基础能力优先实现到 `apps/backend`
- `apps/api` 只在有明确迁移需要时保留或提炼参考，不继续作为正式服务端扩展
