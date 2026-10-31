## ADDED Requirements

### Requirement: Coalesce only equivalent in-flight CN state reads
国服 Web MUST 仅在同一适配器、API base、认证生命周期、用户/凭据和 auth 模式下合并尚未完成的 `/web/state` 请求，MUST NOT 缓存已完成的成功或失败结果。各调用方 MUST 得到独立状态对象。

#### Scenario: Concurrent equivalent reads
- **WHEN** 同一有效身份同时发起多个普通状态读取且首个仍未完成
- **THEN** 仅发出一次网络读取，并为各调用方返回等价且互不共享可变引用的状态

#### Scenario: A subsequent read needs current data
- **WHEN** 前一次请求成功或失败后再次读取
- **THEN** 发起新的权威网络请求，不命中成功 TTL 或失败缓存

#### Scenario: Authentication scopes differ
- **WHEN** 不同账号、匿名/认证模式、不同凭据或同账号退出再登录发起读取
- **THEN** 不加入旧作用域请求，旧响应不能回填新身份

### Requirement: Preserve cancellation and authentication recovery
系统 MUST 让每个调用方独立取消，MUST 保持合法同会话401刷新与重试，MUST NOT 通过迟到刷新复活已退出或已切换的身份。

#### Scenario: One consumer cancels
- **WHEN** 共享读取中的一个调用方取消而其它调用方仍等待
- **THEN** 仅该调用方取消，其它调用方正常得到结果；全部调用方取消后资源有界释放

#### Scenario: Access token refresh is legitimate
- **WHEN** 同一仍有效会话的状态读取遇到401并完成令牌刷新
- **THEN** 正常重试并返回状态，后续读取使用新凭据，且无额外登录要求

#### Scenario: Logout or switch wins over refresh
- **WHEN** 刷新或状态读取在退出/换账号前开始、在其后返回
- **THEN** 迟到结果不覆盖当前登录状态或页面数据，取消不导致清除新的有效会话

### Requirement: Respect explicit refresh and mutation barriers
系统 MUST 为显式刷新和影响聚合状态的变更提供权威读取屏障，包括独立资料/计费/模拟/简历客户端。MUST 覆盖可能已由服务器提交的失败结果，且不得因高频诊断/心跳而无谓失效。

#### Scenario: State changes while a read is pending
- **WHEN** 资料删除/上传、会员或支付同步、面试创建/结束/删除等变更与旧读取重叠
- **THEN** 变更后的读取不加入变更前请求，迟到响应不回填已失效状态

#### Scenario: Explicit refresh and telemetry traffic
- **WHEN** 用户显式刷新，或仅有ACK/心跳等诊断流量
- **THEN** 显式刷新读取最新状态；单纯诊断流量不改变状态读取合并资格，原收音和SSE合同保持
