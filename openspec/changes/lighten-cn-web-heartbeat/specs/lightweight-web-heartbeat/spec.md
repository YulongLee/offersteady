## ADDED Requirements

### Requirement: Ordinary heartbeats use one lightweight authoritative read
普通页面心跳 MUST 仅读取一次必要会话状态，不加载资料、配置、对话、积分或会员内容，不缓存会话结束状态。

#### Scenario: Live or preparing heartbeat with multiple materials
- **WHEN** 合法用户对准备中或未过期的进行中会话提交心跳，且会话绑定多份资料
- **THEN** 仓库执行一次心跳投影读取且资料读取/刷新次数为零，不写会话或计费记录

#### Scenario: PostgreSQL projection excludes deleted sessions
- **WHEN** 心跳投影读取不存在或已软删除的会话
- **THEN** 返回不存在，不读取大 JSON 字段且服务返回原 404

### Requirement: Authorization and idle semantics remain authoritative
系统 SHALL 校验归属，并保持现有准备、正常、预警、过期、结束的时间边界和错误响应。

#### Scenario: Different owner submits heartbeat
- **WHEN** 请求用户不是会话所有者
- **THEN** 返回原 403，且不更新活动记录或页面租约

#### Scenario: Idle session expires
- **WHEN** 已开始的 live 会话超过原空闲期限
- **THEN** 调用现有 idle-timeout 终止及资源释放流程，成功后返回原 409 ended，失败不得返回成功心跳

#### Scenario: Session ends between consecutive heartbeats
- **WHEN** 一次心跳后会话权威状态变为 ended
- **THEN** 下一次心跳即时读到 ended 并返回原 409，不续租

### Requirement: Existing leases and material-aware paths are unchanged
优化 MUST 保持网页租约、准备/进行页面互通及公开响应字段；非心跳资料读取与回答校验保持原路径。

#### Scenario: Preparing page shares existing live lease
- **WHEN** 同一会话已有未过期 live 租约且准备页提交心跳
- **THEN** 按原规则返回 live 租约，不覆盖它

#### Scenario: Live page claims lease
- **WHEN** 带 pageInstanceId 的 live 页面提交心跳
- **THEN** 使用原原子租约 claim，保持 generation 与到期字段

#### Scenario: Material-aware session operation reads changed material
- **WHEN** 非心跳操作读取完整会话且资料发生变化
- **THEN** 仍按原规则刷新绑定资料，不因优化跳过可用性校验

### Requirement: Verification and CN cutover are bounded and safe
发布 MUST 以实际国服运行镜像为基线，自测通过且重复空闲门禁后只切换后端；测试内容 MUST 合成，禁止生产压测或创建收费面试。

#### Scenario: Protected user work exists
- **WHEN** 有进行中面试、近期准备/页面/音频活动、运行中的模拟面试或受保护后台任务
- **THEN** 拒绝切换并保持现有运行容器不变

#### Scenario: Candidate passes and CN is idle
- **WHEN** 回归与候选验证通过，重复门禁确认空闲
- **THEN** 仅部署心跳范围改动，模型/环境/配置及其它容器不变，失败回滚原镜像

#### Scenario: Synthetic performance comparison
- **WHEN** 在相同合成数据与并发负载下比较旧和新心跳
- **THEN** 输出查询/资料读取次数、样本量、P50/P95/P99、失败数，并标明不是线上整体 P95 提升承诺
