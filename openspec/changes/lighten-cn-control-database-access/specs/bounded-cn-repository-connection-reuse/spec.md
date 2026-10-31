## ADDED Requirements

### Requirement: Enable bounded reuse only inside explicit CN backend lifecycle
连接池 MUST 默认关闭，MUST 仅在CN Backend显式生命周期与配置允许时覆盖authentication/session两个热点仓库。该进程同配置 MUST 共用有界总池，MUST 限定连接数量、等待队列和借用时长；其它仓库、Global与worker MUST 保留原连接路径。

#### Scenario: Feature is disabled or region differs
- **WHEN** 开关关闭、区域为Global或worker未激活Backend生命周期
- **THEN** 使用原短连接参数与行为，不因导入或环境开关建立池

#### Scenario: Two hot repositories borrow concurrently
- **WHEN** 同配置auth和session仓库在已激活CN生命周期内同时执行
- **THEN** 共用同一有界池，连接总数不按仓库倍增，正常返回等价数据

#### Scenario: Capacity or wait budget is exceeded
- **WHEN** 所有池连接被持有且等待达到时限或队列上限
- **THEN** 有界失败，不无限等待、不旁路创建额外短连接、不报告业务成功

### Requirement: Preserve transaction freshness and configuration identity
复用 MUST 保留原上下文提交/回滚、cursor行为与行级事务规则，MUST NOT 缓存权限/用户/资料/权益结果或自动重放写入。不同数据库或连接选项 MUST NOT 误共享；fork后的子进程 MUST NOT 借父池连接。

#### Scenario: Write fails or explicit rollback occurs
- **WHEN** 池内业务执行抛错、SQL失败或显式回滚
- **THEN** 原回滚结果保持，归还后的下一借用可正常执行，失败写入不被重放

#### Scenario: Permission or session changes after a completed read
- **WHEN** 账号/会话状态在另一次事务中改变后再次使用同一物理连接
- **THEN** 新SQL观察当前权威状态，不因复用恢复旧授权或旧会话

#### Scenario: Connection configuration or process differs
- **WHEN** 第二个运行域使用不同DSN/options或子进程继承父状态
- **THEN** 不借错库或继承活连接，冲突安全拒绝或按明确独立原路径处理

### Requirement: Clean resources on every lifespan exit
系统 MUST 在正常关闭、启动失败、同配置多app退出及延迟归还场景正确清理资源，不因一个app退出破坏仍活跃的同配置app。

#### Scenario: Startup fails before application yield
- **WHEN** 池激活后其它启动步骤失败
- **THEN** 对应运行域的连接和后台资源仍被释放，不残留活动池

#### Scenario: App closes while a borrower is returning
- **WHEN** 生命周期退出且有连接尚在归还，或另一个同配置app仍在运行
- **THEN** 不强行重放/提交未知业务，按引用和池关闭合同释放连接并拒绝已关闭运行域新借用
