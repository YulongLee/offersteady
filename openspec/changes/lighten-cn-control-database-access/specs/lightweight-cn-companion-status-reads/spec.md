## ADDED Requirements

### Requirement: Read only necessary authoritative CN control session fields
国服伴随绑定状态解析 MUST 使用包含session ID、owner、status、mode、audio mode的权威轻量投影，MUST NOT 为该查询读取/刷新资料或写回会话。已软删除会话 MUST 视为不存在；legacy空模式 MUST 保持原默认。

#### Scenario: Bound session has many documents
- **WHEN** 国服解析绑定且会话有多份资料
- **THEN** 每个不同候选会话只读必要字段、资料读取和会话写入为零，绑定响应与原算法等价

#### Scenario: Missing deleted or foreign session
- **WHEN** 会话不存在、软删除或请求owner不符
- **THEN** 保持原404/403服务合同及pairing错误转换，不增加跨用户可见性

### Requirement: Preserve lifecycle leases modes and material-aware authority
轻量化 MUST 保持既有pinned绑定、generation、租约、心跳时限、采集状态、interview/written/mock及audio模式判断，MUST NOT 改变心跳或轮询频率。Global与真正资料感知业务 MUST 保持原完整读取。

#### Scenario: Session changes between eligible reads
- **WHEN** 会话结束、删除或模式改变并跨过既有pairing缓存边界再次读取
- **THEN** 返回当前权威结果，不新增控制投影TTL，租约与绑定替换处理保持

#### Scenario: Normal capture and formal answer
- **WHEN** 合法用户正常收音、提交回答或资料变更后进行业务操作
- **THEN** 仍经过原owner、会话状态及完整资料校验，不依赖控制投影绕过业务门禁

#### Scenario: Global binding read
- **WHEN** 产品区域为Global
- **THEN** 沿原完整读取与绑定判断，不启用国服轻量分支
