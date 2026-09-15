## Why

旧版桌面助手仍可绑定并进入面试，可能继续使用已知的连接/资源问题。需要在服务端做权威版本门禁，同时降低心跳和会话回收对数据库的额外压力。

## What Changes

- 绑定桌面助手和开始面试前校验同平台、同架构的最新可发布版本；明确落后时拒绝进入并提示更新。
- 保留版本未知时的兼容降级，避免无法上报版本的开发设备被误伤。
- 会话资源回收继续使用统一、幂等的 watchdog；桌面心跳不再为每次请求查询全部绑定。
- 仅先部署国际服，国服待用户验证后再发布。

## Impact

- Backend realtime binding/start path and tests.
- Web receives a clear update-required error; existing download center remains the update entry point.
- No URL, payment, or data migration changes.
