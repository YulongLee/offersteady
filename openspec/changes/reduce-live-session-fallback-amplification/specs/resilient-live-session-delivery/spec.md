## ADDED Requirements

### Requirement: Healthy session stream is the primary state source
活动面试网页 SHALL 在收到会话 SSE 的首个权威 snapshot 后，将该流作为 runtime、transcripts、question candidates 和 events 的主要状态来源，并停止周期性并行查询这些状态接口。

#### Scenario: First snapshot arrives
- **WHEN** 活动面试页收到当前会话 SSE 的首个有效 snapshot
- **THEN** 页面标记实时流健康、取消恢复查询，并继续通过增量事件单调更新界面

#### Scenario: Stream remains healthy
- **WHEN** 会话 SSE 持续交付 keepalive 或增量事件
- **THEN** 页面不得每秒并行查询 runtime、transcripts、question candidates 和 events

### Requirement: Disconnection recovery is bounded and non-overlapping
网页 SHALL 使用单一、可取消的恢复调度器处理 SSE 断线，先立即重连，再使用 2、4、8、15 秒封顶的退避，并确保任意时刻最多一个恢复 snapshot 请求在途。

#### Scenario: Stream disconnects
- **WHEN** 已健康的会话 SSE 意外关闭且会话仍活动
- **THEN** 页面保留现有可见状态、立即尝试重连，并在连续失败时进入有界退避

#### Scenario: Stream recovers
- **WHEN** 重连后的 SSE 交付权威 snapshot
- **THEN** 页面取消所有重连和 fallback 定时器且不得继续后台恢复查询

#### Scenario: Session terminates or page becomes inactive
- **WHEN** 会话进入终态或当前页面失去活动租约
- **THEN** 页面关闭 SSE 并取消全部恢复工作

### Requirement: Recovery uses one authoritative snapshot
Backend SHALL 提供一个经过现有用户授权与页面租约校验的会话恢复 snapshot，返回当前 runtime、transcripts、question candidates、events 和 continuation cursor；原有独立接口 MUST 保持兼容。

#### Scenario: Client performs initial hydration
- **WHEN** 当前版 Web 首次进入活动面试或 SSE 无法在预算内交付首 snapshot
- **THEN** Web 使用一次聚合 snapshot 请求恢复完整当前状态

#### Scenario: Older client queries individual endpoints
- **WHEN** 旧版 Web 调用现有 runtime、transcripts、question candidates 或 events 接口
- **THEN** Backend 按原有契约返回结果且不要求客户端升级

### Requirement: Same-browser duplicate subscriptions are coordinated
支持 `BroadcastChannel` 的浏览器中，同一会话的多个标签页 SHALL 协调一个主页面维持 SSE 和恢复请求，其他页面 SHALL 通过浏览器内消息接收同一状态；不同设备不得被该机制限制。

#### Scenario: Second tab opens the same interview
- **WHEN** 同一浏览器已有活动主页面且第二个标签页打开同一会话
- **THEN** 第二页成为 follower，不创建第二条主 SSE 或周期性恢复请求

#### Scenario: Leader closes
- **WHEN** 主页面关闭、隐藏超出租约或停止 heartbeat
- **THEN** 一个仍活动的 follower 接管领导权并恢复 SSE，且状态不得倒退

#### Scenario: Same account uses another device
- **WHEN** 用户在另一台电脑或手机打开同一允许访问的会话
- **THEN** 浏览器内协调不得阻止该设备建立自己的实时连接
