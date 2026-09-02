## ADDED Requirements

### Requirement: High-frequency state updates are entity scoped
设备心跳、网页心跳和会话活动版本更新 MUST 只持久化当前实体，且 MUST NOT 因单条高频更新序列化或写入完整实时运行态快照。

#### Scenario: Stable desktop sends a heartbeat
- **WHEN** 已登记设备发送一次心跳
- **THEN** 系统只更新该设备状态与必要索引，并以现有响应契约返回

#### Scenario: Live page renews its lease
- **WHEN** 当前面试页面续约 live lease
- **THEN** 系统只更新当前用户和会话的租约，不重写其他设备、会话、候选或字幕

### Requirement: Incremental state remains recoverable and backward compatible
仓库 MUST 能从升级前全局快照恢复，并以更新的实体状态覆盖同一对象；旧桌面客户端和公开 API MUST 继续兼容。

#### Scenario: First start after deployment uses legacy data
- **WHEN** 新实体存储为空而旧快照包含设备、绑定和网页租约
- **THEN** 仓库幂等补齐新实体状态并保持原设备代码和绑定可用

#### Scenario: Entity state is newer than legacy snapshot
- **WHEN** 重启时同一设备同时存在于旧快照和实体状态
- **THEN** 仓库使用时间戳或 generation 更新的实体状态

### Requirement: Activity versions remain monotonic
每个会话的活动版本 MUST 原子地单调增加，且一次更新 MUST NOT 重写其他会话的活动字段。

#### Scenario: Transcript and event updates interleave
- **WHEN** 同一会话交错保存字幕和运行事件
- **THEN** 后续读取的活动版本严格不回退且其他会话字段不被重写

### Requirement: Product behavior is unchanged
状态存储优化 MUST NOT 改变 ASR、音频、Partial/Final、字幕合并、回答、截图、计费、UI、权限或隐私行为。

#### Scenario: Existing interview completes after upgrade
- **WHEN** 旧版伴随程序完成绑定、收音、字幕、快答和截图回答
- **THEN** 用户观察到的协议、内容顺序、扣分次数和操作方式与基线一致
