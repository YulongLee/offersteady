## Context

当前设备使用固定机器码登记，网页创建 session binding，桌面助手轮询 pairing status 后创建 publisher。问题在于旧 binding、旧 publisher 和旧网页订阅分别恢复，缺少“本场连接”的唯一切换点。用户已经确认每场面试由网页选择设备，并且一个账号同一时间只启用一场实时面试。

## Goals / Non-Goals

**Goals:**

- 在准备页提供连接上次设备和输入机器码两个明确入口。
- 两个入口复用同一个服务端绑定方法，并为本场创建新 binding。
- 新绑定原子使同一用户或同一设备的其他 binding 与 publisher 失效。
- 桌面助手在 binding 变化或 publisher 永久失效时停止旧连接并重建。
- 桌面助手通过轻量设备租约自动发现当前 binding，不轮询需要网页登录身份的 session runtime。
- 旧网页 session 收到替换信号后停止订阅。

**Non-Goals:**

- 不支持同一账号并行进行多场实时面试。
- 不修改 ASR 模型、音频格式、RAG、回答 Prompt 或页面整体原型。
- 不在本轮引入长期设备密钥体系；设备凭据作为后续安全加固项。

## Decisions

### Decision 1: User selects the device on the preparation page

网页显示最近一次属于当前用户且仍在线的设备摘要。用户可以一键连接，也可以输入新的机器码。替代方案是助手自动连接最近 session，但它无法表达用户当前意图，容易再次连接错误面试。

### Decision 2: Both UI choices call one binding operation

一键连接只把后端返回的最近设备机器码提交给既有 binding 入口，不创建第二套绑定逻辑。这样机器码校验、旧连接关闭和事件记录保持一致。

### Decision 3: Enforce one active binding per user and per device

绑定时扫描同一用户与同一设备的 bound 记录，将非目标记录标记为 stale，并关闭对应 publisher。面试历史记录保留，不删除字幕或回答；“单面试”只约束实时连接。

### Decision 4: Treat permanent publisher errors as terminal

WebSocket `1008` 和服务端 `401/403/404/409/410` 不得使用旧 token 重连。桌面 publisher 停止、清空队列，并由 pairing-status 发现当前 binding 后创建新 publisher。普通网络断开仍使用有限指数退避。

### Decision 5: Use binding identity as the desktop effect boundary

桌面端 publisher 生命周期依赖 `bindingId + sessionId + bindingGeneration`，而不是只依赖 sessionId。任何字段变化都销毁旧 publisher，避免同 session 重绑后仍复用旧 token。

### Decision 6: Backend owns a lightweight active-connection lease

桌面助手以稳定的 `deviceId + machineCode` 查询 active-connection。后端返回当前 binding、session 状态和由 `bindingId + bindingGeneration` 组成的 leaseVersion。助手以一秒周期跟随该租约，不再高频调用需要网页登录身份且包含多组 Redis 聚合的 runtime 接口。设备状态上报同样由当前 active binding 校验，不依赖网页 access token。

### Decision 7: Publisher creation is single-flight per source

后端为同一用户、session、source 和客户端创建新 publisher 前关闭旧 publisher，避免网络抖动或客户端重建留下并行发布通道。旧 token 返回永久失效，不允许音频跨 binding 路由。

### Decision 8: Binding replacement retires the provider ASR pipeline

新 binding 不只关闭旧 publisher，还必须立即关闭旧 session 的麦克风与系统音频 Provider ASR 长连接，清空其待处理 partial 队列，并阻止已经取出的旧任务继续发布。当前 session 更换设备时重置 Provider 连接但不退休 session。外层 ASR 超时必须主动关闭故障连接，且不得再次等待同样的长超时；后续新音频由当前 binding 建立干净连接。

## Risks / Trade-offs

- [Risk] 一键连接暴露机器码可能增加肩窥风险 → 页面只显示设备名称、在线状态和掩码机器码，提交时使用后端返回值。
- [Risk] 切换面试会中断另一个已打开页面 → 页面明确说明继续后会切换，并由后端保证确定性。
- [Risk] Redis 快照并发更新可能出现短暂竞争 → 使用既有 Redis repository 写锁完成 binding/publisher 更新。
- [Risk] 暂未引入正式 device credential → 当前仍以固定机器码加设备 ID 校验，后续商业安全加固时迁移，不阻塞本轮稳定性修复。

## Migration Plan

1. 先发布兼容的新查询接口和单用户绑定约束。
2. 发布网页双入口，旧的手动机器码入口继续由同一 API 处理。
3. 发布桌面助手，使新 binding identity 触发 publisher 重建。
4. 观察 `401/404/410` 重试计数，确认旧客户端请求自然退出。
5. 回滚时可恢复旧网页布局；服务端单用户约束可保留，不影响旧客户端绑定。

## Open Questions

- 正式商业版本是否将固定机器码升级为一次性 pairing code 与可刷新 device credential。
