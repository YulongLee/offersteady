## Why

2026年11月6日国服只读巡检发现4次模拟面试控制通道在客户端断连后，finally关闭再次抛出WebSocketDisconnect。实际1724镜像中该分支只捕获RuntimeError；已上线的麦克风关闭修复未覆盖控制通道。

## What Changes

- 仅补全模拟面试控制通道最终关闭的预期断连异常处理，保留任务取消、旧连接资源归属、暂停与计费规则。
- 增加真实路由层断连、重连替换、取消与重复收尾的合成回归，先证明旧版失败再验证修复。
- 用户2026年11月7日明确授权开发、自测通过后部署国服。仅在新鲜核对实际运行基线、全部空闲/归属门禁通过后切换CN Backend，并独立验收。

## Capabilities

### New Capabilities
- `cn-mock-control-close-safety`: 控制通道收尾容忍已断开连接并保持既有资源、取消、计费和发布边界。

### Modified Capabilities

无；历史能力尚未归档到主spec，本变更补齐控制端点缺陷。

## Impact

业务增量限定`apps/backend/app/modules/mock_interview.py`。生产基线为实际Backend1724/df78，238输入中237份保持，203Schema/344配置/44依赖/辅助上传格式/助手1.3.6 d7/Web366份与七非目标保持。Web、助手、Global、worker、模型、收费、连接池、SQL及其他慢请求优化不在范围。测试仅合成数据；私有配置和原始日志留服务器，不提交推送Git。
