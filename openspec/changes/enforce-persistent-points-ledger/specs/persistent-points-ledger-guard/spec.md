## ADDED Requirements

### Requirement: 商业用户身份必须持久化
系统 SHALL 在配置PostgreSQL后使用持久化认证仓库。同一手机号再次登录 MUST 解析为同一个 `user_id`，数据库不可用时 MUST 拒绝登录或账户写入，不得创建临时内存身份。

#### Scenario: 同一手机号跨重启登录
- **WHEN** 用户使用同一手机号在后端重启前后完成登录
- **THEN** 系统返回相同的持久化 `user_id`

#### Scenario: 认证数据库不可用
- **WHEN** 已配置PostgreSQL但认证仓库无法连接
- **THEN** 系统明确失败且不创建内存用户

### Requirement: 积分账本必须持久化
系统 SHALL 在配置PostgreSQL后将余额、赠送、购买、兑换和消费流水全部写入持久化账本。数据库不可用时 MUST 阻止新的积分读取和写入，不得回退到进程内余额。

#### Scenario: 后端重启后读取余额
- **WHEN** 用户已经拥有积分流水且后端服务重启
- **THEN** 系统从PostgreSQL恢复相同余额和流水

#### Scenario: 计费数据库不可用
- **WHEN** 已配置PostgreSQL但计费仓库无法连接
- **THEN** 系统明确失败且不创建新的内存余额、赠送或扣费记录

### Requirement: 新用户赠送必须跨重启幂等
系统 SHALL 为每个持久化 `user_id` 最多创建一条200点 `welcome_grant`，并 MUST 使用数据库唯一引用保证并发请求和服务重启不会重复发放。

#### Scenario: 重复读取积分状态
- **WHEN** 同一用户多次读取积分状态或并发触发赠送检查
- **THEN** 账本中始终只有一条 `welcome_grant`

#### Scenario: 服务重启后再次检查
- **WHEN** 已领取赠送积分的用户在服务重启后再次访问
- **THEN** 系统保留原余额且不新增赠送流水

### Requirement: 测试内存仓库必须显式隔离
系统 MAY 在自动化测试或未配置数据库的纯原型场景使用内存仓库，但该模式 MUST NOT 在已配置数据库的运行环境中作为故障降级路径。

#### Scenario: 自动化单元测试
- **WHEN** 测试直接构造内存服务且没有请求商业持久化
- **THEN** 测试可以继续使用合成内存数据
