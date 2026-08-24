## Why

线上单场面试会把后台请求量从空闲约 38 次/分钟放大到约 175 次/分钟，并把控制接口 P95 推高到约 0.8–1.4 秒。主要原因是会话 SSE 不稳定时，网页每秒并行查询四个完整状态接口，重连期间还可能产生重复订阅；需要在不改变收音、回答和截图业务语义的前提下降低恢复流量和尾延迟。

## What Changes

- 将活动面试的统一 SSE 作为网页状态主通道；收到首个权威 snapshot 后停止并行高频状态查询。
- 为 SSE 断线建立单实例、可取消的立即重连与 2/4/8/15 秒有界退避，连接恢复后清理全部恢复定时器。
- 新增一次返回 runtime、transcripts、question candidates 和 events 的会话恢复 snapshot 接口，保留原四个接口兼容旧客户端。
- 同一浏览器的多个面试页通过页面租约与 `BroadcastChannel` 协调，只允许一个活动页维持主 SSE；不限制不同设备访问。
- 增加不含对话正文的连接建立、首快照、连接时长、关闭原因、重连与 fallback 遥测，并将控制 API、恢复 snapshot 和 SSE 建连指标分开统计。
- 增加单页、多页、断网恢复、旧接口兼容和 1/5/10 会话合成负载回归测试。
- 不修改 ASR 模型与切片、Prompt、回答触发规则、积分/支付、截图处理语义或桌面助手协议；本轮无需重新发布桌面客户端。

## Capabilities

### New Capabilities

- `resilient-live-session-delivery`: 规定活动面试网页如何以 SSE 为主、以合并 snapshot 为有界恢复路径，并避免同一浏览器重复订阅与请求放大。
- `realtime-delivery-observability`: 规定实时通道与控制接口的分层、无内容遥测和性能验收口径。

### Modified Capabilities

无。

## Impact

- Web：活动面试订阅生命周期、恢复调度、跨标签页协调及 Backend adapter。
- Backend：新增只读会话 snapshot 聚合接口、实时连接遥测及容量指标分类。
- API：新增恢复 snapshot 端点；现有 runtime、transcripts、question-candidates、events 和 SSE 端点保持兼容。
- Deployment：Backend 与 Web 可分阶段发布并独立回滚，不需要数据库迁移或桌面助手更新。
- Privacy：遥测只记录时延、计数、关闭原因和匿名技术标识，不新增音频、截图、问题、回答、简历或资料正文的持久化。
