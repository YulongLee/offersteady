## ADDED Requirements

### Requirement: Grant one welcome balance
系统 SHALL 在用户首次完成有效账号验证后发放一次且仅一次 200 点测试积分，并 MUST 记录可审计的赠送流水。

#### Scenario: New verified user receives points
- **WHEN** 从未领取过欢迎积分的用户完成有效账号验证
- **THEN** 系统写入一笔 200 点 `welcome_grant` 并更新余额

#### Scenario: User signs in again
- **WHEN** 已领取欢迎积分的用户再次登录或重复触发注册回调
- **THEN** 系统返回原发放结果且不得再次增加 200 点

### Requirement: Maintain an immutable points ledger
系统 MUST 使用整数点数和不可变流水记录赠送、购买、兑换码入账、预留、结算、释放、退款、兑换冲正与人工调整，并 SHALL 让用户查看不含内部敏感信息的余额明细。

#### Scenario: User opens points history
- **WHEN** 用户查看积分明细
- **THEN** 系统按时间展示变动类型、点数、关联订单或用量、状态和变动后余额

#### Scenario: Support adjusts points
- **WHEN** 获授权人员完成规定的人工调整审批
- **THEN** 系统新增调整流水并记录操作人、原因和审计标识，而不是修改历史流水

### Requirement: Credit one-time redemption codes into the existing wallet
系统 SHALL 只接受服务端验证的一次性积分兑换码，并 MUST 在同一原子事务中写入唯一 `redemption_credit` 流水和标记兑换码已使用。兑换积分 MUST 进入现有钱包并遵循会员优先规则，客户端不得提交可信点数值。

#### Scenario: Valid points code is redeemed
- **WHEN** 已登录用户成功兑换一枚由服务端定义为 100 点的有效一次性码
- **THEN** 系统将现有钱包增加 100 点并只写入一次关联兑换记录的流水

#### Scenario: Redemption is replayed
- **WHEN** 同一账号重放已成功的兑换请求或再次提交自己已兑换的码
- **THEN** 系统返回原兑换结果且不新增积分、流水或独立余额

#### Scenario: Member redeems points
- **WHEN** 有效会员用户成功兑换积分
- **THEN** 积分保留在同一钱包，普通回答继续优先使用会员权益

### Requirement: Meter answers with configurable integer rates
系统 SHALL 从服务端费率目录读取普通回答和截图回答点数；初始建议费率为普通回答 5 点、截图回答 15 点，并 MUST 在预留时保存费率快照。

#### Scenario: Normal answer succeeds
- **WHEN** 积分用户以 5 点费率成功获得一条普通回答
- **THEN** 系统结算 5 点并写入关联该回答用量 ID 的流水

#### Scenario: Screenshot answer succeeds
- **WHEN** 积分用户以 15 点费率成功获得一条截图回答
- **THEN** 系统只结算 15 点且不得再叠加普通回答费用

### Requirement: Reserve and settle usage idempotently
系统 MUST 为每次计费操作使用唯一用量 ID，在创建任务前预留积分，并 MUST 只在成功交付可用回答后结算一次。

#### Scenario: Client repeats a request
- **WHEN** 客户端、队列或回调使用同一用量 ID 重复提交
- **THEN** 系统返回同一计费结果且不得重复预留或结算

#### Scenario: AI task fails
- **WHEN** 回答生成失败、超时、取消或截图无法识别
- **THEN** 系统释放预留积分并在余额明细中展示未扣费结果

### Requirement: Meter knowledge indexing from server Token quotes
系统 SHALL 对新知识材料使用 200 点最低消费和每 1,000 Token 20 点的版本化服务端报价；15 天和 30 天会员可优先使用对应权益段的两份知识材料额度。

#### Scenario: Knowledge quote crosses ten thousand Tokens
- **WHEN** 服务端计数为 10,001 Token 且用户没有可用会员额度
- **THEN** 系统报价并预留 220 点，成功后只结算一次

### Requirement: Reject insufficient balance safely
系统 MUST 原子地检查可用余额和预留积分，余额不足时 MUST 不启动新的付费处理任务。

#### Scenario: Concurrent requests exceed balance
- **WHEN** 多个并发请求合计费用超过可用余额
- **THEN** 系统只预留余额可覆盖的请求，并对其他请求返回余额不足

### Requirement: Handle refunds and reversals through ledger entries
系统 SHALL 根据已公布退款规则使用新流水撤销或调整权益，并 MUST 不删除原购买和使用记录。

#### Scenario: Paid points order is refunded
- **WHEN** 一笔符合规则的积分包订单完成退款
- **THEN** 系统写入退款撤销流水、保留原购买记录并防止余额变为未处理的负数

### Requirement: Collect unit economics without content
系统 SHALL 为计费操作记录模型、语音、存储、支付和人工成本估算，但 MUST 不在成本日志中记录问题正文、回答正文、截图或资料内容。

#### Scenario: Operator reviews gross margin
- **WHEN** 运营查看商品或会员用量的单位经济报告
- **THEN** 系统展示聚合收入、成本、退款和估算毛利，不暴露面试敏感内容
