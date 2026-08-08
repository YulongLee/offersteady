## ADDED Requirements

### Requirement: Desktop screenshot polling has one owner
每个桌面助手实例 MUST 只有一个远程截图任务轮询所有者，且 MUST NOT 因 renderer 重载、窗口隐藏或 React effect 重建而创建并行截图轮询器。

#### Scenario: Companion starts and renderer mounts
- **WHEN** 桌面主进程启动且 renderer 完成挂载
- **THEN** 只有主进程查询远程截图任务，renderer 不再发起相同查询

#### Scenario: Companion window is hidden
- **WHEN** 用户关闭窗口使助手隐藏到托盘
- **THEN** 助手保留处理有效 live 面试截图的能力，但不得启动额外轮询器

### Requirement: Screenshot task polling requires a live binding
桌面助手 SHALL 先确认设备已登记、绑定有效且 session 状态为 live，只有满足这些条件时才查询下一笔截图任务。

#### Scenario: Device is registered but not bound
- **WHEN** pairing status 表示设备在线但没有有效绑定
- **THEN** 助手不得查询截图任务，并以不短于 10 秒的空闲间隔再次探测绑定

#### Scenario: Bound session is not live
- **WHEN** 设备已绑定但 session 仍在 preparing、ready 或 ended 状态
- **THEN** 助手不得查询截图任务

#### Scenario: Bound session is live
- **WHEN** pairing status 表示有效绑定且 session 为 live
- **THEN** 助手 SHALL 以低延迟间隔查询截图任务，并继续使用既有捕获、上传和失败回报链路

### Requirement: Polling is non-overlapping and backs off after failures
所有桌面绑定与截图探测 MUST 等待上一笔请求完成后再安排下一笔；连续网络或服务错误 SHALL 使用有上限的退避，MUST NOT 维持一秒级失败请求。

#### Scenario: Request takes longer than the nominal interval
- **WHEN** 一次状态或截图请求尚未完成
- **THEN** 计时器不得启动同类并行请求

#### Scenario: Backend is unavailable repeatedly
- **WHEN** 连续状态探测失败
- **THEN** 下一次探测间隔逐步增加且最大不超过 30 秒，成功后恢复正常间隔

### Requirement: Idle screenshot queries are normal empty results
后端 MUST 将未登记、未绑定、绑定失效、非 live 和没有待处理截图视为只读查询的正常空闲结果，返回成功 envelope 与 `data=null`，且 MUST NOT 记录为告警级领域错误。

#### Scenario: Old companion polls without a binding
- **WHEN** 旧版本助手直接调用下一笔截图接口但当前没有有效绑定
- **THEN** 后端返回 HTTP 200 和 `data=null`，不抛出 `desktop-capture-binding` 领域错误

#### Scenario: No screenshot is pending during a live interview
- **WHEN** 有效 live 设备查询但没有待处理截图
- **THEN** 后端返回 HTTP 200 和 `data=null`

#### Scenario: Desktop attempts a state-changing upload with invalid identity
- **WHEN** 无效设备或机器码尝试上传、认领或失败回报截图
- **THEN** 后端继续拒绝该写操作，不因空闲查询兼容而放宽授权

### Requirement: Idle polling does not keep interviews active
绑定状态和空截图查询 MUST NOT 更新面试业务活动时间，MUST NOT 创建截图任务或写入重复绑定记录。

#### Scenario: Companion stays idle for an extended period
- **WHEN** 助手只执行低频 pairing status 与空截图查询
- **THEN** 面试活动时间、截图任务数量和绑定代际保持不变
