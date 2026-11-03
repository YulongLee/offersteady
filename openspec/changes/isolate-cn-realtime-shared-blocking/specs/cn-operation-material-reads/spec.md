## ADDED Requirements

### Requirement: Batch authoritative documents within one CN operation
CN非mock单次get_session资料刷新及RAG metadata过滤 MUST 对同文档去重并在支持时使用一次statement批量读取，MUST 将本次缺失保留为缺失，MUST NOT 跨请求缓存权限或资料。无批读实现 MUST 兼容逐唯一ID读取；list_sessions、Global和mock版本选择 MUST 保持。

#### Scenario: Shared documents and duplicate chunks
- **WHEN** 合成会话绑定多份资料，多个候选片段来自同一文档
- **THEN** 每个操作只需一次权威批读或逐唯一ID fallback，原文档/候选输出、顺序、score及owner/status/version/kind/collection过滤保持

#### Scenario: Concurrent edit deletion and prefetch completion
- **WHEN** 文档在操作之间修改/删除/换owner或版本，或预取运行期间资料变化
- **THEN** 下一次操作及预取末尾独立重读并拒绝旧指纹结果；单次批读可使用同一statement快照，不取消前后两个权威检查
