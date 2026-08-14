## ADDED Requirements

### Requirement: Referral activation is limited to newly registered accounts
系统 SHALL 仅允许账号在服务端记录的注册时间起 72 小时内激活其他用户的邀请链接。资格判定 MUST 使用服务端时间，不得信任浏览器时间；已成功建立的历史邀请关系不受窗口到期影响。

#### Scenario: New account activates within three days
- **WHEN** 尚未激活邀请的账号在注册时间后不超过 72 小时提交另一用户的有效邀请链接
- **THEN** 系统继续执行邀请激活与双方奖励事务

#### Scenario: Activation window has expired
- **WHEN** 账号在注册时间超过 72 小时后提交邀请链接
- **THEN** 系统返回“新用户注册后 3 天内可激活邀请链接”，且不创建邀请关系或积分流水

#### Scenario: Activation is submitted at the boundary
- **WHEN** 服务端接收激活请求的时间恰好等于注册时间加 72 小时
- **THEN** 该请求仍被视为在有效期内

### Requirement: Successful activation rewards both accounts atomically
有效邀请激活 SHALL 在同一个数据库事务内为分享链接的用户和新用户分别写入一条唯一积分流水，并保存邀请关系、双方奖励额度和配置版本快照。任一写入失败 MUST 回滚关系和双方全部积分。

#### Scenario: First valid activation rewards both users
- **WHEN** 符合时间和一次性约束的邀请首次激活，分享者奖励为 500 点且新用户奖励为 500 点
- **THEN** 分享者余额增加 500 点，新用户余额增加 500 点，并分别出现一条可识别的邀请奖励流水

#### Scenario: Activation is retried or submitted concurrently
- **WHEN** 同一新用户对同一邀请链接重复或并发提交激活
- **THEN** 数据库最终只保存一个邀请关系、分享者一条奖励流水和新用户一条奖励流水，双方余额各只增加一次

#### Scenario: Either reward insertion fails
- **WHEN** 保存分享者或新用户任一积分流水失败
- **THEN** 邀请关系和另一方积分流水一并回滚，客户端收到可重试失败

### Requirement: Growth administrators configure both rewards
后台增长设置 SHALL 分别配置分享者奖励积分和新用户奖励积分，并展示 3 天激活窗口。两个奖励 MUST 为 1–100000 的整数，更新 MUST 受 `growth.manage` 权限、变更原因、版本和审计保护。

#### Scenario: Administrator saves both reward values
- **WHEN** 有权限的管理员填写合法的分享者奖励和新用户奖励并保存
- **THEN** 后续新激活按该配置版本的两项额度分别入账，历史激活和流水保持不变

#### Scenario: Either reward value is invalid
- **WHEN** 任一奖励为零、负数、非整数或超过上限
- **THEN** 服务端拒绝整次配置更新且当前生效配置不变

### Requirement: Referral eligibility and mutual rewards are visible
积分与会员页 SHALL 在用户提交前说明只有注册后 3 天内可以激活，并展示分享者与新用户各自可获得的积分。页面 SHALL 使用服务端返回的资格状态和截止时间；超过有效期后 MUST 禁用提交并展示不可激活原因。

#### Scenario: Eligible user reviews referral activation
- **WHEN** 注册未满 3 天且尚未激活邀请的用户打开积分与会员页
- **THEN** 页面显示可激活截止时间、剩余资格和“你与好友都将获得积分”的具体额度

#### Scenario: Ineligible user reviews referral activation
- **WHEN** 注册已超过 3 天且尚未激活邀请的用户打开积分与会员页
- **THEN** 页面显示激活期限已过且不再提供可提交的激活按钮

#### Scenario: Already activated user reviews referral status
- **WHEN** 用户已经成功激活过邀请
- **THEN** 页面保持已激活状态并展示当次奖励结果，不因 72 小时窗口后来到期而撤销积分
