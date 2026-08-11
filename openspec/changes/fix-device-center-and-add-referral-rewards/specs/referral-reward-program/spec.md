## ADDED Requirements

### Requirement: Each user has one safe referral link
系统 SHALL 为每个登录用户按需生成一个稳定、不可枚举且 URL-safe 的公开邀请码，并在积分与会员页展示由服务端公共 Web 地址组成的分享链接。链接 MUST NOT 包含用户 ID、手机号、设备标识或服务端密钥。

#### Scenario: User opens referral card for the first time
- **WHEN** 登录用户首次打开积分与会员页的邀请区域
- **THEN** 服务端创建并返回一个专属邀请码和可复制分享链接

#### Scenario: User opens referral card again
- **WHEN** 同一用户再次读取邀请状态
- **THEN** 系统返回原有邀请码和链接，不重复创建或使历史链接失效

### Requirement: Referral activation is explicit and account authenticated
邀请链接 SHALL 打开说明邀请关系和奖励对象的公开落地页。积分与会员页 SHALL 同时为尚未激活邀请的登录用户提供粘贴完整分享链接或邀请码的入口。两种入口的激活都 MUST 由登录用户明确确认；未登录用户完成登录后 SHALL 能恢复待激活邀请码，但前端缓存本身不得视为成功。

#### Scenario: Visitor activates after login
- **WHEN** 未登录访问者从有效邀请链接选择“登录并激活”并完成登录
- **THEN** Web 恢复邀请码、调用认证激活接口并显示服务端确认结果

#### Scenario: Invalid referral code is opened
- **WHEN** 访问者打开不存在、格式错误或已撤销的邀请码
- **THEN** 页面显示链接不可用且不创建邀请关系或积分流水

#### Scenario: Logged-in user activates from billing
- **WHEN** 尚未激活邀请的登录用户在积分与会员页粘贴另一用户的完整分享链接或邀请码并确认激活
- **THEN** Web 解析邀请码、调用认证激活接口、显示服务端确认结果并刷新当前邀请状态

#### Scenario: Billing activation is no longer available
- **WHEN** 当前账号已经成功激活过邀请或管理员关闭邀请活动
- **THEN** 积分与会员页不允许再次提交激活，并明确展示已激活或活动暂停状态

### Requirement: Each invitee activates at most once
每个账号 MUST 终身最多作为被邀请人成功激活一个其他用户的邀请码，且 MUST 禁止邀请人激活自己的链接。相同请求重试 SHALL 幂等返回原成功结果；已激活后尝试另一邀请码 SHALL 被拒绝。

#### Scenario: First valid activation
- **WHEN** 未激活过邀请的用户提交另一用户的有效邀请码且功能已开启
- **THEN** 系统创建唯一邀请关系并进入奖励事务

#### Scenario: Activation request is retried
- **WHEN** 同一被邀请人再次提交已经成功激活的同一邀请码
- **THEN** 系统返回原激活结果且不新增关系或积分

#### Scenario: Invitee tries a different referral
- **WHEN** 已激活过邀请的用户提交另一用户的邀请码
- **THEN** 系统返回“每个账号只能激活一次”且不改变原关系

#### Scenario: User tries self referral
- **WHEN** 用户提交自己的邀请码
- **THEN** 系统拒绝自邀且不创建关系或积分

### Requirement: Referral reward is atomic and ledger based
成功激活 SHALL 在同一个数据库事务内保存关系、配置版本与奖励积分快照，并为邀请人写入一条唯一 `referral_credit` 积分账本记录。被邀请人本轮 SHALL 不获得额外积分。任一步失败 MUST 回滚全部变化。

#### Scenario: Activation succeeds
- **WHEN** 有效邀请满足一次性约束且当前奖励为 500 点
- **THEN** 系统只为邀请人增加 500 点、在积分明细显示邀请奖励，并保存一次激活记录

#### Scenario: Concurrent activation is submitted
- **WHEN** 同一被邀请账号或同一激活请求并发提交多次
- **THEN** 数据库最终只存在一个激活关系和一条奖励账本，邀请人余额只增加一次

#### Scenario: Ledger insertion fails
- **WHEN** 保存奖励账本失败
- **THEN** 激活关系一并回滚，客户端收到可重试失败而不是部分成功

#### Scenario: Multiple billing repositories initialize in production
- **WHEN** 兑换码、管理后台和计费仓库以任意顺序初始化或重启
- **THEN** 最终数据库账本约束仍允许 `referral_credit`，且一次真实 PostgreSQL 激活能够原子写入关系和奖励流水

### Requirement: Admin controls referral availability and reward amount
后台管理平台 SHALL 提供邀请奖励启用开关和单次奖励积分配置。更新 MUST 要求 `growth.manage` 权限、1–100000 的整数额度、变更原因和管理员审计，并记录配置版本与更新时间。

#### Scenario: Administrator enables referrals
- **WHEN** 有权限的管理员保存有效奖励额度并开启功能
- **THEN** 新的有效激活按当前配置快照为邀请人入账

#### Scenario: Administrator disables referrals
- **WHEN** 有权限的管理员关闭邀请奖励
- **THEN** 新激活返回活动暂停，历史邀请码、关系和已发积分保持不变

#### Scenario: Invalid reward amount is submitted
- **WHEN** 管理员提交零、负数、非整数或超过上限的额度
- **THEN** 服务端拒绝更新且当前生效配置不变

### Requirement: Referral status is visible without exposing invitees
邀请人 SHALL 在积分与会员页看到当前开关状态、单次奖励、成功邀请人数和累计奖励。普通用户响应 MUST NOT 暴露被邀请人的手机号、用户 ID、设备或其他个人资料。

#### Scenario: Inviter reviews results
- **WHEN** 邀请人打开积分与会员页
- **THEN** 页面显示聚合邀请次数和累计奖励，并可在现有积分明细查看对应入账
