## ADDED Requirements

### Requirement: Reuse owner-scoped raw documents within one CN aggregate read
国服 `/web/state` MUST 能将本次已取得的原始当前用户资料记录复用于本次会话绑定刷新，MUST 保留原显示响应、排序、重名消歧和绑定字段算法。记录 MUST NOT 跨请求缓存或进入额外公共响应。

#### Scenario: Many sessions share documents
- **WHEN** 多个同用户会话绑定了本次列表已经取得的资料
- **THEN** 复用原始记录而不再次逐份查询，并与原状态响应及绑定结果等价

#### Scenario: Duplicate display names exist
- **WHEN** 两份资料显示名重复且列表采用消歧显示
- **THEN** 列表继续消歧，绑定继续使用原始资料名称，不把展示投影误当原记录

### Requirement: Preserve authority for missing, foreign and changing records
仅 owner/document ID 一致的记录 SHALL 可用于 seed；没有覆盖的引用 MUST 使用原权威查询。下一次请求 MUST 重新读取资料状态。

#### Scenario: Filtered or deleted reference is missing
- **WHEN** 绑定引用未出现在非删除列表或列表被过滤
- **THEN** 走原 get_by_id 路径，保留不存在/删除/未就绪的原处理，不从列表缺失直接推断状态

#### Scenario: A foreign or mismatched seed is supplied
- **WHEN** 内部 seed 包含其它 owner 或键与 document ID 不一致的记录
- **THEN** 该记录不可作为命中，不得增加跨账号可见性或跳过原权限处理

#### Scenario: Document version or status changes between reads
- **WHEN** 前一请求完成后资料版本、ready/index状态、删除状态或内容元数据变化
- **THEN** 下一请求反映当前权威记录，不使用旧请求缓存，revision与来源算法保持

#### Scenario: Mock and Global behavior remain unchanged
- **WHEN** 会话为模拟面试，或请求属于Global及非聚合入口
- **THEN** 保留模拟面试选定版本短路及原读取行为，不引入额外收费/写入或不相关区域变化
