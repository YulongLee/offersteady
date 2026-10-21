## Why

用户于2026-10-21要求先验证现有百炼接口是否可调用 `deepseek-v4.1-flash-1017`，打通后完成本地开发、自测，留待晚上另行替换版本。目标是把现有文本与截图推理统一到经过验证的型号，同时保留当前产品能力。

## What Changes

- 对国服及国际服各自现有文本、视觉凭据和接口做有界的合成探针，验证非思考、流式、单图/最多四图、结构化输出和国服联网工具。
- 接入成功后，分别从 `release-cn-20261019.2` 与 `release-global-20261019.1` 准备独立候选：共享文本、快答、详答与视觉四个现有模型配置指向1017，保留四个独立选择字段。
- 各资料worker只更新自身实际存在的文本模型配置；必要时仅补齐摘要非思考参数，保留8秒预算及本地提取式回退。
- 增加合成评测、供应商适配器回归和可审阅的配置增量/发布准备说明；不以请求成功冒充质量或性能全面提升。
- 本轮不切换、重启或重配生产，不推送Git；后续发布需重新获部署指令并通过最新用户工作保护门禁。

## Capabilities

### New Capabilities

- `verified-model-1017-routing`: 现有两服文字与截图模型的有界验证、独立候选配置和非目标保持。

### Modified Capabilities

无。既有产品流程、输出契约、费用和功能开关均保持。

## Impact

涉及服务端模型配置候选、必要的最小供应商兼容代码、合成eval和测试/探针工具。真实供应商调用使用既有服务端凭据，只传合成文字/图片，不创建真实用户会话、资料任务或账务，不输出密钥/私有地址/用户数据。ASR、TTS、embedding、rerank、MinerU、前端、助手及PDF模板不在变更范围。

## Global authorized production phase - 2026-10-22

The user explicitly authorized synchronizing CN performance optimizations and models to Global and deploying them. This later phase supersedes the earlier local-only delivery limit solely for Global Backend and material-worker. Audit existing auth/state/prefetch parity first and preserve already published changes. Overlay each component own actual image with only the summary non-thinking line and update four Backend model selectors plus the old worker existing shared selector to1017. Web, CN, Admin, companion, billing, membership and Git publishing are outside scope.
