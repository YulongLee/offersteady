## ADDED Requirements

### Requirement: Persist CN runtime entities without global snapshot network locking
CN候选、账号设备关联及绑定更新 MUST 使用实体/会话级原子持久化，MUST NOT 在全局runtime锁内执行网络写或整份快照重写。原owner、版本/时间顺序、绑定索引、活动版本及失败合同 MUST 保持；Global MUST 保持原路径。

#### Scenario: Candidate update while another session ingests
- **WHEN** 一场面试更新候选且Redis写变慢，另一场面试访问receipt
- **THEN** 慢写不持全局内存锁跨I/O，不重写整份snapshot，候选及索引持久化可恢复且不同owner不混淆

#### Scenario: Multiple instances and reordered saves
- **WHEN** 两个新代码实例竞争seed或保存不同版本/状态
- **THEN** 原子规则不允许旧版本、错误owner或过期bound状态覆盖更新值，不报告未持久化成功

### Requirement: Recover legacy state and fence retired sessions
新CN代码 MUST 兼容读取旧snapshot并安全seed缺失实体，MUST 保留旧key而不续期旧snapshot，MUST 不覆盖新实体。clear MUST 原子建立退役保护并保留原stale binding及账号历史；MUST 阻止旧snapshot、内存和晚到保存复活已清理状态。保护期限 MUST 覆盖旧snapshot残存及新runtime期限；不得允许未修改旧writer混跑。

新CN绑定envelope及索引 MUST 使用独立命名空间，旧v1值 MUST 保持可由旧代码解码。stale状态 MUST 原子持久化且数组/数值精度不变；保护及索引寿命 MUST 覆盖其它会话活动续命的实体，缺索引 MUST 避免后续每次读取都全扫。

#### Scenario: Cold start with legacy snapshot and updated entities
- **WHEN** 旧snapshot仍存在且新实体已有较新状态，进程重启或并发seed
- **THEN** 新状态优先，已缺失/退役状态不由旧snapshot复活，全部原读取合同和账号历史保持

#### Scenario: Clear races with seed or late candidate
- **WHEN** clear与seed/候选写并发，或退役后重启/旧snapshot临近过期
- **THEN** clear幂等，退役后候选/活跃绑定不能复活；合法未clear重绑仍可用，restart新sessionId不受旧保护影响

### Requirement: Resolve a pinned CN binding by its authoritative session and owner index
CN配对读取携带完整pinnedSessionId/pinnedBindingId且仓库支持新可选定点方法时，MUST 沿现存session→owner索引读取该owner/session的canonical绑定及retired状态，MUST NOT 为有效pin查找读取全站绑定、执行全站HVALS或逐个解码无关历史。定点观察 MUST 为原子只读，不续TTL、修改索引/状态或增加跨请求缓存。有效pin查询和解码工作量 MUST 不随无关历史绑定总量增长。

manualCode、deviceId、pinnedSessionId、pinnedBindingId、owner、binding generation、新鲜度、bound/stale及retired校验 MUST 保持，并 MUST 继续数据库权威会话状态检查。正常pin缺失、请求身份不匹配或pin失效 MUST 保持原released与latest fallback，不猜测归属、不把失效pin报告为held；内部owner/session元数据不一致或JSON损坏 MUST 按既有错误合同传播并fail closed，MUST NOT 伪装成正常miss或通过latest fallback掩盖。未实现新可选方法的仓库 MUST 保留原路径；Global、mocks及旧助手HTTP协议 MUST 不变。

#### Scenario: Valid pin remains constant work as unrelated history grows
- **WHEN** 相同有效pin、canonical绑定和索引分别与1、1191及10000条合成绑定共存，新增项均为无关历史
- **THEN** 三种规模的定点Redis查询次数和解码数量保持固定，全站HVALS调用均为零，pin结果与原有效绑定语义相同；混合轮询仍满足该命中路径约束

#### Scenario: A pin is missing or fails identity and liveness checks
- **WHEN** pin不完整或不存在，session/owner索引缺失，manualCode/deviceId/bindingId/generation与请求不匹配，或绑定已退役/失效、数据库会话missing/ended
- **THEN** 旧pin不被报告为held，沿原顺序进入latest fallback并执行既有校验，不跳过权限/权威状态检查或改变错误响应

#### Scenario: Internal pinned metadata is corrupt
- **WHEN** session/owner索引与canonical绑定内部owner/session元数据不一致，或保存的JSON无法解码
- **THEN** 按既有错误合同传播并fail closed，不将内部损坏当作正常pin未命中，不进入latest fallback掩盖损坏或猜测归属

#### Scenario: Pinned lookup races with retirement, end or rebind
- **WHEN** 定点读取与retire、数据库end或新generation/rebind交错
- **THEN** 绑定、owner与retired在原子读取边界一致；先被观察到的退役/替换/ended不得返回旧pin为held，原缓存generation失效及合法新绑定/latest回退保持，结果能按读取与权威校验顺序解释，不复活已退役会话

#### Scenario: Existing repository or non-CN consumer uses the prior contract
- **WHEN** 既有仓库没有新可选定点方法，或调用来自Global/mocks/旧助手
- **THEN** 维持原可用路径、HTTP字段、generation/重绑/停止语义，不强制新抽象接口或助手升级
