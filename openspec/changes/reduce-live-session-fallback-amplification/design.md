## Context

当前 Web 已有统一会话 SSE，但 `App.tsx` 在流不健康时每秒调用 `loadRealtimeSession`，后者并行读取 transcripts、question candidates、events 和 runtime。线上单场面试采样中，这四个接口各出现约 114 次，并伴随约 12 次 SSE 建连；请求量由空闲约 38 次/分钟上升到约 175 次/分钟。PostgreSQL 与 Redis 没有锁等待或连接耗尽，机器也未发生 cgroup throttling，表明主要问题是恢复请求放大和同步存储调用排队，而不是模型或数据库容量不足。

系统必须保留现有回答专用 SSE、统一会话事件、旧状态接口、跨设备访问和显式回答边界。本轮只触及 Web 与 Backend，不要求用户更新桌面助手。

## Goals / Non-Goals

**Goals:**

- 健康 SSE 下不运行四接口的周期性完整刷新。
- SSE 断线时提供单调、有界、非重叠恢复，不清空用户当前可见内容。
- 同一浏览器只保留一个活动会话主订阅，避免重复标签页放大请求。
- 用一个聚合 snapshot 代替四个独立恢复请求，同时保持旧端点兼容。
- 将控制请求、恢复请求与长连接建连分别度量，能定位真实长尾。
- 通过功能回归与合成并发验证请求量、P95、CPU 和错误率。

**Non-Goals:**

- 不改变 ASR、音频帧、问题确认、回答生成、截图、资料检索或计费逻辑。
- 不限制同一账号在不同设备上使用。
- 不引入 WebSocket、Kafka、新数据库表或新的第三方服务。
- 不删除旧的状态查询接口，不发布新桌面安装包。

## Decisions

### 1. 以首次 snapshot 作为 SSE 健康门槛

浏览器只有在连接收到首个可解析的权威 snapshot 后才标记 stream healthy，并立即取消恢复定时器；仅 `EventSource.onopen` 不足以证明代理链路已经交付业务数据。断线时保留当前 reducer 状态，不把页面回退为空白或“正在安全加载”。

替代方案是完全信任 `onopen`。该方式无法识别代理建立 HTTP 连接但没有转发事件的半连接，因此不采用。

### 2. 单一恢复调度器与有界指数退避

每个页面实例只允许一个 reconnect timer 和一个 in-flight snapshot。断线后先立即重连；仍失败则按 2、4、8、15 秒退避并在 15 秒封顶，加入小幅随机抖动以避免多个用户同时重连。收到 snapshot、页面失活或会话终止时取消所有恢复工作。

替代方案是固定 1 秒轮询。固定轮询恢复略快，但会在后端或代理异常时持续制造请求风暴，已被线上数据证明不可接受。

### 3. 聚合 snapshot 复用现有服务边界

Backend 新增 `/sessions/{session_id}/snapshot`，在一次授权与租约校验后并发/顺序读取现有四类状态并返回稳定 envelope。首版不新增数据库表，也不改变旧响应模型；旧四端点继续供旧 Web 和显式历史功能使用。Web 仅在初次水合和有界恢复时调用 snapshot。

替代方案是继续由浏览器 `Promise.all` 请求四端点。它会重复认证、路由、中间件、数据库 session 读取和网络往返，无法解决请求量放大。

### 4. 用 BroadcastChannel 协调同浏览器页面领导权

页面使用现有 page instance/lease 语义，并以 `BroadcastChannel` 发送 heartbeat、claim 和 release。当前可见且租约最新的页面成为 leader 并建立 SSE；follower 保留本地 UI，通过浏览器消息接收 leader 的 snapshot/event。浏览器不支持该 API 时退化为现有单页行为，服务端租约仍是最终仲裁。

替代方案是只使用 `localStorage` 锁。它缺少直接消息广播且崩溃恢复更容易留下陈旧锁，因此只作为必要兼容而不作为主实现。

### 5. 分层记录无内容性能指标

Backend 请求窗口按 `control_api`、`recovery_snapshot`、`sse_handshake` 分类；Web 上报 connect、firstSnapshot、connectedDuration、closeReason、reconnectAttempt 和 fallbackSnapshot。所有字段只包含时长、计数、原因枚举、会话技术标识哈希或既有匿名标识，不包含用户内容。

替代方案是继续使用单一 API P95。它把长连接握手、恢复接口和普通业务接口混在一起，无法指导扩容或修复。

## Risks / Trade-offs

- [SSE 真断线时恢复比固定 1 秒轮询慢] → 首次立即重连，保留当前 UI，随后才进入有界退避。
- [BroadcastChannel 领导权竞态] → 服务端页面租约继续仲裁；消息带 page instance 和 epoch，旧 leader 事件不可覆盖新 leader。
- [聚合 snapshot 仍包含同步存储读取] → 路由把同步聚合放入线程执行，且一次恢复只允许一个 in-flight 请求；后续连接池优化单独评估。
- [新 Web 与旧 Backend 发布窗口不兼容] → 先发布 Backend 新端点，再发布 Web；Web 保留旧四端点 fallback，可独立回滚。
- [指标分类改变管理端曲线] → 保留总 P95 兼容字段，同时新增分类字段，避免监控页面断裂。

## Migration Plan

1. 部署兼容 Backend：新增 snapshot 与指标分类，旧端点行为不变。
2. 验证健康、鉴权、snapshot 与旧端点后，发布 Web 的 SSE 主通道和恢复调度器。
3. 先以单实例/单浏览器验证 30 分钟，再执行 5/10 会话合成负载并观察请求率、P95、CPU、SSE 重连和 5xx。
4. 若 Web 出现恢复异常，只回滚 Web 静态版本；Backend 新接口可保留。若 Backend 异常，回滚 Backend，旧 Web 接口仍可用。

## Open Questions

无阻塞问题。PostgreSQL 共享连接池和更多 Uvicorn worker 属于后续架构优化，待本轮消除客户端请求放大并获得新基线后再决定。
