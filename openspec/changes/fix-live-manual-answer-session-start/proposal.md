## Why

当前用户创建面试、确认资料并进入实时面试界面后，手动输入问题调用模型会出现“回答生成失败，请稍后重试”。根因是准备页进入面试时只更新了前端状态并跳转页面，没有调用后端 Session Start API，导致后端仍认为该面试不是 `live` 状态，Chat Service 拒绝生成回答。

现在需要修复“前端已进入面试、后端未开始面试”的状态错位，并把回答失败提示从误导性的“检查积分或会员权益”改为展示真实失败原因。

## What Changes

- 准备页点击“开始面试 →”时，前端必须调用后端 `POST /api/v1/sessions/{sessionId}/start`。
- 后端成功返回 `live` 状态后，前端再更新本地面试状态并进入实时面试页。
- 如果后端启动失败，用户停留在准备页并看到真实错误原因，不进入一个无法回答的实时页面。
- 手动输入问题调用模型失败时，前端展示后端返回的具体错误信息，而不是统一提示“当前任务未启动，请检查积分或会员权益”。
- 保持现有产品原型页面布局、按钮位置和手动输入交互不变。
- 不修改 Chat Service、模型供应商、截图回答、实时语音、支付或积分规则。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `streamlined-interview-entry`: 开始面试必须同步启动后端 Interview Session，并在启动或回答失败时展示真实错误，避免进入前端可见但后端不可回答的假 live 状态。

## Impact

- Affected frontend areas: `apps/web/src/App.tsx`, `apps/web/src/domain.ts`, `apps/web/src/backend-adapter.ts`, 相关测试
- Affected backend APIs: 复用现有 `POST /api/v1/sessions/{sessionId}/start`
- Affected flow: 创建面试 → 确认资料 → 开始面试 → 后端 session 进入 `live` → 手动输入问题 → Chat Service 正常回答
- Affected error handling: Live Answer 请求失败时展示后端真实原因；不再把所有失败都解释成积分或会员问题
- Privacy impact: 无新增数据采集；只同步会话生命周期状态
