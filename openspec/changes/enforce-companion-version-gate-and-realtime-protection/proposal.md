## Why

旧版桌面助手仍可绑定并进入面试，可能继续使用已知的连接/资源问题。需要在服务端做权威版本门禁，同时降低心跳和会话回收对数据库的额外压力。

## What Changes

- 国服在绑定桌面助手和开始面试前校验同平台、同架构的最新可发布版本；版本落后或无法验证时拒绝进入并提示更新。
- 面试准备页在机器码输入区直接说明最新版要求，已连接旧版助手时禁用开始按钮并提供下载入口。
- 恢复网页与桌面控制面 10 秒轮询提示和服务端 10 秒查询缓存，避免旧发布基线把请求频率回退到约 1 秒。
- 会话资源回收继续使用统一、幂等的 watchdog；桌面心跳不再为每次请求查询全部绑定。
- 自测通过后，仅在国服无进行中面试、网页会话和 ASR 音频流时部署。

## Impact

- Backend realtime binding/start path and tests.
- CN Web receives a clear blocking update-required state; existing download center remains the update entry point.
- No URL, payment, or data migration changes.
