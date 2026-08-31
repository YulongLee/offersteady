## Why

生产监控显示伴随程序的连接状态与设备状态请求占普通 API 流量的大多数，并在单 Uvicorn worker 下放大同步数据库访问的排队，造成 API P95 长尾。需要在不改变实时收音、回答、截图、计费和用户界面的前提下，减少无意义控制面请求并让监控正确区分长连接持续时间与普通 API 延迟。

## What Changes

- 将桌面助手等待绑定探测改为服务端建议驱动的非重叠自适应间隔，并保留既有 2 秒 live 租约刷新，降低空闲请求频率且不降低会话内恢复性能。
- 仅在设备状态发生语义变化或保活到期时上报 `device-status`，失败时保留重试，不丢失状态转换。
- 稳定远程截图 SSE 的生命周期，避免捕获状态的短暂变化反复销毁和重建连接。
- 将截图与实时语音 SSE 从普通控制 API 延迟中单独分类，保留独立连接时长指标，避免长连接持续时间污染 API P95。
- 增加轮询、状态去重、SSE 生命周期和指标分类回归测试，并在生产发布前后对比请求量与延迟。
- 不增加 Uvicorn worker，不改变 Redis 运行态一致性模型，不修改 ASR、快答、截图回答、计费、布局或隐私边界。

## Capabilities

### New Capabilities

- `companion-control-plane-efficiency`: 定义桌面助手控制面自适应轮询、状态上报去重、截图 SSE 单连接和无损恢复行为。
- `runtime-latency-classification`: 定义普通 API 与 SSE 连接时长的独立统计口径和回归可观测性。

### Modified Capabilities

<!-- No established main spec requirements are changed. -->

## Impact

- Desktop: `apps/desktop` 的绑定轮询、设备状态上报和远程截图 SSE 生命周期。
- Backend: 管理容量请求分类与摘要，不改变现有业务 API 响应协议。
- Tests/docs: 桌面轮询与主进程测试、后端容量指标测试、发布验证记录。
- Privacy: 不新增音频、转录、截图或用户资料持久化；诊断指标只记录路由类别、耗时和计数。
