## ADDED Requirements

### Requirement: Price knowledge indexing from a server catalog
系统 MUST 从版本化服务端目录读取知识材料最低消费和 Token 单价。对于包含有效可索引文本的文档，点数 MUST 按 `max(200, ceil(tokenCount / 1000) × 20)` 计算；客户端提交的 Token 数或费用不得作为可信结算依据。

#### Scenario: Document contains 3,000 Tokens
- **WHEN** 服务端 tokenizer 对规范化文本计数为 3,000 Token
- **THEN** 系统报价 200 点最低消费

#### Scenario: Document contains exactly 10,000 Tokens
- **WHEN** 服务端计数为 10,000 Token
- **THEN** 系统报价 200 点

#### Scenario: Document crosses the minimum tier
- **WHEN** 服务端计数为 10,001 Token
- **THEN** 系统按 11 个计费单位报价 220 点

#### Scenario: Document has no usable text
- **WHEN** 解析结果没有可索引文本
- **THEN** 系统返回无法索引状态且不得预留或结算 200 点最低消费

### Requirement: Disclose a versioned quote before indexing
系统 SHALL 在创建计费索引任务前展示服务端 Token 数、计费单位、预计点数、权益来源、预计余额、目录版本和报价有效期。报价过期、内容变化或目录变化时 MUST 重新报价并再次确认，不得静默提高已确认费用。

#### Scenario: Points user reviews an upload
- **WHEN** 积分用户上传文件且服务端完成解析报价
- **THEN** 确认界面展示 Token 数、`200 点起 / 每 1,000 Token 20 点`规则、本次费用和扣费后预计余额

#### Scenario: Quote expires before confirmation
- **WHEN** 用户在报价过期后尝试确认索引
- **THEN** 系统拒绝旧报价、返回新报价并等待用户重新确认

#### Scenario: Server count differs from client estimate
- **WHEN** 客户端估算与服务端 tokenizer 结果不同
- **THEN** 系统只使用服务端报价且在用户确认前展示差异后的最终预计费用

### Requirement: Include two knowledge indexing allowances in long passes
每个新生效的 15 天或 30 天会员权益段 MUST 包含 2 份知识材料索引额度；3 天和 7 天会员 MUST NOT 包含该额度。额度 SHALL 在对应权益段开始时生效，在该权益段结束时失效，且不得扣减用户已有积分。

#### Scenario: Fifteen-day pass becomes active
- **WHEN** 用户的 15 天会员权益段开始生效
- **THEN** 系统显示 2 份可用知识材料额度及其到期时间

#### Scenario: User has a seven-day pass
- **WHEN** 7 天会员用户请求知识材料报价
- **THEN** 系统不提供会员知识材料额度并按积分公式报价

#### Scenario: Eligible pass is queued behind another pass
- **WHEN** 用户购买的 15 天会员将在当前会员结束后顺延生效
- **THEN** 两份知识材料额度仅在该 15 天权益段实际开始时可用

#### Scenario: Long-pass allowance expires unused
- **WHEN** 15 天或 30 天权益段结束时仍有未使用额度
- **THEN** 未使用额度失效且不得转换为积分或延长到其他权益段

### Requirement: Consume one allowance only for a usable document index
一份会员额度 SHALL 覆盖一份符合公开文件限制并成功交付可用索引的知识文档版本。系统 MUST 在处理前锁定额度，仅在成功后消费；失败、取消或未改变内容的幂等重试 MUST 释放或复用额度，不得重复消费。

#### Scenario: Member indexes a document successfully
- **WHEN** 有两份可用额度的 30 天会员成功建立一份文档索引
- **THEN** 系统消费一份额度、剩余一份且本次不扣积分

#### Scenario: Member indexing fails
- **WHEN** 使用已锁定会员额度的解析或索引任务失败
- **THEN** 系统释放该额度、保留原剩余额度且不扣积分

#### Scenario: Member repeats the same request
- **WHEN** 客户端以相同用量 ID 或未改变内容重复提交
- **THEN** 系统返回原索引结果或用量记录且不再次消费额度

#### Scenario: Member has used both allowances
- **WHEN** 15 天或 30 天会员已成功消费两份额度后上传新材料
- **THEN** 系统按照 Token 公式展示积分报价并在确认后使用积分钱包

### Requirement: Keep empty collections free and count document versions explicitly
创建空知识库集合 SHALL 继续免费且不得消耗会员额度。替换文件内容形成新文档版本并重新建立索引时 MUST 作为新的索引用量报价或消费一份可用额度。

#### Scenario: Member creates an empty collection
- **WHEN** 用户新建一个不含文档的知识库集合
- **THEN** 系统不扣积分且不减少两份知识材料额度

#### Scenario: Indexed content is replaced
- **WHEN** 用户用不同内容替换已索引文档并请求建立新版本索引
- **THEN** 系统为新文档版本创建独立报价并明确其积分或额度来源

### Requirement: Settle knowledge usage idempotently and privately
知识索引用量 MUST 使用稳定用量 ID 和报价快照，在任务成功后只结算一次，并在失败或取消时释放积分或额度。计费、分析与成本日志 MUST NOT 记录文件名、知识正文或内容片段。

#### Scenario: Points indexing succeeds
- **WHEN** 积分已预留且对应文档版本成功交付可用索引
- **THEN** 系统按确认的报价快照结算一次并写入 Token 数、费率版本和用量 ID 流水

#### Scenario: Indexing is cancelled
- **WHEN** 用户在可用索引交付前取消任务
- **THEN** 系统释放完整积分预留或会员额度锁定，并记录不含文档内容的安全状态

#### Scenario: Operator reviews knowledge cost
- **WHEN** 运营查看知识索引单位经济数据
- **THEN** 系统只展示聚合 Token、点数、权益来源与成本，不暴露文件名称或知识内容

### Requirement: Preserve historical quotes and entitlements during migration
新目录发布后，未过期且已确认的旧报价 MUST 保留原费率快照；历史结算和已使用会员额度 MUST NOT 被重写。新规则只适用于新报价和新生效的合格会员权益段。

#### Scenario: Old 20-point quote was already confirmed
- **WHEN** 新目录发布前的 20 点知识索引报价已被用户确认且仍可执行
- **THEN** 系统按原报价快照完成或释放该用量，而不是改收 200 点

#### Scenario: New upload follows catalog migration
- **WHEN** 新目录生效后用户创建新的知识材料报价
- **THEN** 系统使用 200 点最低消费和 Token 阶梯规则

