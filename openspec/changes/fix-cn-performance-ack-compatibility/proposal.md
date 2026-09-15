## Why

国服发布时混用了新版 performance-ack 路由和旧版实时服务。路由传入 route_received_at_ms 等三个参数，服务签名不接受，导致真实上报请求返回 500。用户已确认修复此故障。

## What Changes

- 恢复三个既有可选时间戳参数的接收与诊断记录，保持旧客户端兼容。
- 对当前运行代码的独立快照进行先失败、后通过的接口回归测试。
- 以运行镜像为唯一部署基线，仅替换修复文件；保留原镜像，空闲时切换并验证。

## Capabilities

### New Capabilities

- `runtime-performance-ack-compatibility`: 明确性能上报的可选字段兼容、内容最小化和安全修复验收约束。

### Modified Capabilities

无；本变更恢复既有行为，不扩展产品能力。

## Impact

- Backend RealtimeSpeechService.acknowledge_runtime_timing 和回归测试。
- 仅部署国服 Backend，不修改国服前端、国际服、数据库、模型、提示词或内存回收策略。
- 测试只用合成标识和时间戳，不读取用户内容，不产生真实面试或模型费用。
