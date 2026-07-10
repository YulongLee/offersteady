## Why

当前产品在“创建面试 → 开始面试 → 手动输入问题”这条主链路上还不稳定：新建面试存在失败场景，最近面试缺少数量治理与删除维护，开始面试仍暴露出不必要的令牌前置门槛，而实时回答有时没有真正走 `.env` 中配置的真实模型。这个问题已经直接影响原型可用性，需要先把核心面试入口和真实回答链路打通。

## What Changes

- 修复首页/面试入口中新建面试无法成功创建的问题，确保用户创建成功后能进入准备页并看到可继续的会话。
- 将“最近面试”列表限制为最多展示和保留 5 条可恢复记录，并为用户提供明确的删除维护入口。
- 调整 Web 端“开始面试”行为：手动输入模式进入实时面试时不再要求用户先具备额外令牌或发布凭证，服务端在会话启动时自行完成必要状态初始化。
- 拉通实时手动回答链路，确保快答/手动问题输入通过后端真实 Chat Service 与 `.env` 中已配置的模型供应商执行，不再落回 mock、占位回答或错误的本地生成路径。
- 统一开始面试、新建面试和模型回答失败时的真实错误反馈，避免把创建失败、会话未启动、模型未配置等问题混成同一种提示。
- 不修改现有页面主布局、积分体系、截图回答、实时语音、支付或登录主流程。

## Capabilities

### New Capabilities

- `recent-interview-roster-maintenance`: 定义最近面试列表的数量上限、排序、删除维护和超额处理行为。
- `live-manual-answer-runtime`: 定义实时面试页手动问题/快答使用真实后端模型链路、状态反馈与错误呈现行为。

### Modified Capabilities

- `streamlined-interview-entry`: 开始面试与新建面试必须创建并同步可用的后端会话状态，且 Web 手动模式开始面试不得要求额外令牌前置条件。

## Impact

- Affected frontend areas: `apps/web/src/App.tsx`, `apps/web/src/backend-adapter.ts`, `apps/web/src/app-adapter.ts`, 最近面试列表与实时面试页相关测试
- Affected backend areas: Interview Session create/start APIs、live answer/chat APIs、聚合首页状态接口
- Affected runtime dependencies: `.env` 中的模型供应商配置、Chat Service、Authentication、Interview Session
- Affected user flow: 首页新建面试 → 准备页 → 开始面试 → 手动输入问题/快答 → 真实模型回答 → 最近面试维护
- Privacy impact: 不新增数据采集；仍由服务端持有模型密钥与会话初始化逻辑，客户端不保存服务端令牌
