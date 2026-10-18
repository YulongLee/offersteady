## ADDED Requirements

### Requirement: Owned versioned inputs and controlled normalization
国服 SHALL 提供中文简历优化入口，绑定登录用户自己的 ready 简历版本，可附自有 ready JD 版本或限长粘贴 JD 与目标岗位。非法、跨账号、删除、类型/版本不符或过长输入 MUST 在收费与模型前拒绝。受控 MinerU 表格 SHALL 仅在优化输入副本经 HTMLParser 转成有分隔文本，保留全部事实，统一用于展示/模型/引用/改写；未知或主动 markup MUST 拒绝，原文件/Parser/面试快照 MUST 不变。

#### Scenario: General and targeted review
- **WHEN** 用户选择自有 ready 简历，可选提供 JD/目标岗位
- **THEN** 服务锁定准确版本；无 JD 标记岗位匹配未评估，有 JD 仅按实际提供内容分析

#### Scenario: Invalid or foreign input
- **WHEN** 输入跨账号、非 ready、版本失配、已删、超限或含未知/可执行 markup
- **THEN** 不读出他人正文，不计费、不排队、不调用模型，并给中文可恢复错误

#### Scenario: Controlled parsed table
- **WHEN** MinerU 正文含受控表格及日期、联系方式、实体和数字
- **THEN** 所有单元格内容与顺序完整保留，原存储产物不改且无外部资源访问

### Requirement: Independent daily member benefit and points pricing
所有当前有效国服时间会员 SHALL 按 Asia/Shanghai 自然日获得三次独立免费优化，含 1 天/周/月和既有管理员授予时间权益；积分包本身 MUST NOT 授予会员资格。非会员和免费次数已预留/用完的会员 SHALL 每次支付 100 积分，不占其他功能日次数，不新增钱包或更改既有套餐。

#### Scenario: Active members use today's benefit
- **WHEN** 任意有效时间会员依次创建并完成当日前三个免费优化
- **THEN** 每次收费为零，当日免费余量依次从3减至2、1、0，其他功能免费次数保持

#### Scenario: Non-member or daily excess
- **WHEN** 非会员或当日免费额度已占用的会员确认创建
- **THEN** 服务端报价为 100 积分，与是否拥有积分包或会员套餐时长无关

#### Scenario: Midnight and prior-day release
- **WHEN** 北京时间过零点或昨日任务延迟失败
- **THEN** 新日有独立三次免费额度，昨日释放不能额外增加新日额度

#### Scenario: Concurrent requests for the last free allowance
- **WHEN** 当日已完成两次免费优化后，同账号并发创建两个不同任务
- **THEN** 至多一个占用最后免费次数，另一个被既有单任务准入或报价变化门禁拒绝，不允许复用已失效免费报价；任务完成后再次创建报价100积分，失败释放只恢复一次原日次数

### Requirement: Explicit authoritative quote and atomic acceptance
服务端 SHALL 报告会员、业务日、重置时间、免费余量、收费模式、当次积分及可用余额。创建 MUST 绑定用户确认的报价；日期/免费资格/价格变化 MUST 返回冲突要求重新确认，禁止静默扣分。接受付费任务时 MUST 在同一事务、既有 billing-user 锁内写一次 -100 `resume_optimizer_charge`、usage reserved 和 job；免费任务以同事务占用一次原日额度。队列满、源无效、余额不足或写入失败 MUST 不留孤儿扣费/次数。实际扣除使旧消费者立即看到扣后余额。

#### Scenario: Free quote becomes stale
- **WHEN** 用户确认后免费额度被占、会员改变或业务日改变
- **THEN** 返回报价变化，不自动改扣 100 积分，前端重新报价并要求明确确认

#### Scenario: Duplicate or conflicting idempotency
- **WHEN** 同账号重复同一逻辑输入/幂等键，或同键改输入
- **THEN** 相同请求返回原 job 且不重复收费/排队，不同输入返回冲突；跨日重放仍返回原 job

#### Scenario: Insufficient funds or concurrent other spending
- **WHEN** 余额不足或同钱包并发普通回答/模拟面试等消费
- **THEN** 共同账户锁与真实可用余额检查防止超花；失败创建不入队、不留扣费或日次数

### Requirement: Exactly-once terminal accounting
完整有效结果交付为 completed 时 SHALL 与 usage settled 同事务提交，不二次扣积分。失败、取消、源删除、超时、排队过期或中断使任务未交付时 MUST 在同事务释放创建日免费预留，或写唯一 +100 `resume_optimizer_refund` 并 released；旧账本不可变。完成后的删除/取消或导出失败 MUST 不退成功优化费用。编辑/下载/另存完成稿 MUST 不再计费且不要求会员续费。

#### Scenario: Failure cancellation or recovery
- **WHEN** 未完成任务失败、被取消、源删或中断恢复，多次重复终止
- **THEN** 原收费方式只退一次，失败无部分成功稿，迟到模型不能重新结算

#### Scenario: Completion races cancellation
- **WHEN** 完成与取消/源删除并发
- **THEN** 只有一个一致终态胜出，已退不能完成、已完成不能重复退款或扣费

#### Scenario: Completed result after membership expiry
- **WHEN** 会员已过期的 owner 编辑、下载、另存或删除未删完成稿
- **THEN** 不重新收费/占用日次数，删除不恢复成功用量

### Requirement: Failure diagnostics share the existing terminal transaction
固定失败诊断 SHALL 仅保存于既有任务payload，并与failed终态、usage released及唯一原路退款同连接同事务提交，不新增DDL、不改变100积分/每日3次、免费原日释放或原锁序。旧任务无诊断 SHALL 仍可读取，原幂等、取消/源删除屏障和派生正文清理 MUST 保持。

#### Scenario: A diagnosed failure is persisted and replayed
- **WHEN** 合成积分或免费任务校验失败，随后重复处理同一终止回调
- **THEN** 失败原因和释放原子可见，仅退一次原费用/原日次数，不重扣、不产生部分结果

#### Scenario: A later failure arrives after cancellation or source deletion
- **WHEN** 取消或源删已赢得终态屏障，再返回携固定原因的模型失败
- **THEN** 不覆盖终态、不写回派生正文、不重复退款，旧无原因任务保持通用错误兼容
