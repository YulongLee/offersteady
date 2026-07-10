## Why

当前用户进入面试页面后，手动输入问题或点击快答时仍可能收到“模型当前不可用 / 回答生成失败”的提示，即使 `.env` 中已经配置了真实模型地址和密钥。这说明“前端进入面试页 → 后端读取 `.env` → Chat Service 调用真实模型 → 页面展示可用回答或明确错误”的主链路还没有稳定拉通，已经直接影响原型的真实可用性。

## What Changes

- 拉通实时面试页手动提问 / 快答调用真实 Chat Service 的运行时链路，确保后端优先读取 `.env` 中的模型配置，而不是误回退到未配置、占位或测试分支。
- 为 live-answer 模块补充“模型运行时就绪检查”和结构化错误分类，区分会话未启动、模型未配置、鉴权失败、供应商不可达和供应商返回异常等问题。
- 调整实时面试页的错误反馈：当模型不可用时，页面展示后端返回的安全错误原因，并保留原问题以便用户重试，而不是只显示笼统失败提示。
- 补充本地联调与回归验证，覆盖 `.env` 已配置但运行时仍失败的场景，确保手动问题回答不再停留在假联通状态。
- 不修改当前产品原型的页面主布局、资料选择流程、截图回答、实时语音、支付、登录和积分规则。

## Capabilities

### New Capabilities

- `live-model-runtime-readiness`: 定义实时面试问答对 `.env` 模型配置的读取、运行时可用性判断、错误分类和安全反馈行为。

### Modified Capabilities

- `resizable-live-interview-workspace`: 进入面试页后，用户在实时回答区域手动输入问题或点击快答时，系统必须调用后端真实模型链路，并在模型不可用时展示明确可重试的错误状态。

## Impact

- Affected backend areas: `apps/backend/app/services/chat_service.py`, `apps/backend/app/core/config.py`, `apps/backend/app/modules/live_answer.py`, 相关错误映射与日志
- Affected frontend areas: `apps/web/src/App.tsx`, `apps/web/src/backend-adapter.ts`, 实时面试页错误提示与回归测试
- Affected docs: `.env` / 环境变量说明、本地联调说明、必要的集成报告或验证文档
- Affected dependencies: `.env` 中的 `OFFERSTEADY_CHAT_QWEN_BASE_URL`、`OFFERSTEADY_CHAT_QWEN_API_KEY`、`OFFERSTEADY_CHAT_QWEN_MODEL` 和现有 Chat Service / Live Answer API
- Privacy impact: 仍由服务端持有模型密钥；前端只提交会话标识和用户问题，不暴露模型密钥或完整 Prompt
