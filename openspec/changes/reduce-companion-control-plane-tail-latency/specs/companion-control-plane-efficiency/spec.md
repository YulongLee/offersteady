## ADDED Requirements

### Requirement: Binding discovery uses bounded adaptive polling
伴随程序 MUST 在上一笔绑定请求结束后再安排下一笔。等待 live 绑定时 MUST 采用服务端建议且不短于 1 秒的间隔；稳定已绑定状态 MUST 保留不超过 2 秒的租约刷新；连续失败 MUST 使用现有有界退避。

#### Scenario: Waiting companion discovers a live interview
- **WHEN** 伴随程序正在等待绑定且服务端建议 1 秒后刷新
- **THEN** 客户端不得在 1 秒内重复请求，并在下一次成功响应为 live 时立即启动既有面试链路

#### Scenario: Binding request is slow
- **WHEN** 一笔绑定请求执行时间超过正常轮询间隔
- **THEN** 客户端不得并行发起第二笔同类请求

### Requirement: Device status writes are change-driven with keepalive
伴随程序 MUST 在设备状态发生语义变化时立即上报；相同状态在最近一次成功上报后的 15 秒内 MUST 被抑制，超过保活时限 SHALL 再次上报。失败的上报 MUST NOT 被记为成功。

#### Scenario: Stable device remains healthy
- **WHEN** 多次绑定探测得到相同的音频、捕获与连接状态且上次成功上报未超过 15 秒
- **THEN** 客户端只执行绑定读取，不重复提交相同 `device-status`

#### Scenario: Device becomes degraded and recovers
- **WHEN** 状态从健康变为异常，之后恢复健康
- **THEN** 两次语义变化都立即产生一次状态上报

#### Scenario: Status post fails
- **WHEN** 一次变化状态上报失败
- **THEN** 客户端在后续控制周期重试且不得因相同指纹跳过

### Requirement: Screenshot request stream has a single stable owner
桌面主进程 MUST 最多维护一个截图请求 SSE。捕获内部状态在运行态之间切换 MUST 复用现有连接；只有连接资格跨越运行/非运行边界时才启动或停止。

#### Scenario: Capture temporarily reconnects
- **WHEN** 捕获状态从 capturing 变为 reconnecting 或 error 后恢复
- **THEN** 当前截图 SSE 不被主动销毁并重建，且不存在第二个并行连接

#### Scenario: Companion enters eligible runtime
- **WHEN** 捕获状态从非运行态进入运行态且没有活动连接
- **THEN** 主进程立即启动唯一截图 SSE

### Requirement: Interview product behavior remains unchanged
优化 MUST NOT 改变 ASR、实时字幕、快答、截图回答、计费、权限、界面或隐私行为。

#### Scenario: Existing live interview runs after upgrade
- **WHEN** 用户使用升级后的伴随程序进入 live 面试
- **THEN** 音频、字幕、回答与截图仍使用升级前相同协议和业务链路
