# Points Redemption Codes Specification

## Purpose

定义积分兑换码在产品中的发放、兑换、记账、安全保护和页面交互行为。该规范确保兑换码只用于积分入账，不改变既有会员优先、钱包消费和官方支付流程，同时限制泄露、撞库、重复入账和越权操作风险。

## Requirements

### Requirement: Provide points-code redemption on the billing page
积分页面 SHALL 为已登录用户提供独立的兑换码输入和“立即兑换”操作，并 MUST 展示空闲、校验中、成功、不可用、限流和网络失败状态。兑换操作 MUST NOT 要求用户提交交易单号、付款截图或兑换点数。

#### Scenario: User opens the points page
- **WHEN** 已登录用户进入积分页面
- **THEN** 页面在余额和收费说明附近展示兑换码输入、兑换操作和“兑换成功后积分进入当前账号”的说明

#### Scenario: Code input is empty
- **WHEN** 输入为空或只有分隔符与空白字符
- **THEN** “立即兑换”保持禁用并说明需要输入兑换码

#### Scenario: Redemption is pending
- **WHEN** 用户提交格式有效的兑换码且服务端尚未返回最终结果
- **THEN** 页面禁止重复提交同一输入、显示处理中状态并保留现有余额

### Requirement: Trust only the server-defined points value and lifecycle
兑换码的点数、批次、有效期、启用状态和一次性使用限制 MUST 由服务端记录决定。客户端 MUST NOT 发送可信点数值、有效期或状态，也 MUST NOT 通过本地配置或静态资源内置可兑换明文码。

#### Scenario: Client tampers with a points amount
- **WHEN** 客户端在兑换请求中附加或修改点数值
- **THEN** 服务端忽略或拒绝该字段，并只使用兑换码记录中的整数点数

#### Scenario: Valid code is redeemed
- **WHEN** 已登录用户提交一枚处于启用期、未使用且所属批次仍有预算的一次性积分兑换码
- **THEN** 服务端返回实际到账点数、新余额、安全短标识和兑换时间

#### Scenario: Code grants a non-points entitlement
- **WHEN** 兑换码记录试图发放会员、知识库额度、现金或未知权益
- **THEN** 服务端拒绝兑换且不修改任何用户权益

### Requirement: Redeem once with atomic wallet credit
系统 MUST 在一个原子事务中锁定一次性兑换码、创建用户兑换记录并写入一条不可变 `redemption_credit` 积分流水。任何步骤失败时 MUST 全部回滚；同一码不得成功产生两条兑换记录或两次积分入账。

#### Scenario: Redemption succeeds
- **WHEN** 有效兑换请求通过全部校验
- **THEN** 兑换码变为已使用、兑换记录关联当前用户，且钱包余额恰好增加码定义的点数一次

#### Scenario: Two users redeem the same code concurrently
- **WHEN** 两个账号并发提交同一枚未使用兑换码
- **THEN** 只有一个事务成功，另一个收到不可用结果且账本总入账次数为一

#### Scenario: Wallet credit fails
- **WHEN** 锁定兑换码后积分账本写入失败
- **THEN** 整个事务回滚，兑换码仍可在后续安全重试且用户余额不变

### Requirement: Make successful retries idempotent without enabling transfer
每次兑换请求 MUST 携带当前账号范围内的幂等键。相同账号重放已成功的幂等请求 SHALL 返回原成功结果而不重复入账；同一账号再次提交已由自己兑换的码 SHALL 显示原兑换结果；其他账号提交该码 MUST NOT 获得积分或原兑换人的身份信息。

#### Scenario: Successful request is replayed
- **WHEN** 客户端因超时使用相同账号和幂等键重放已成功请求
- **THEN** 服务端返回相同兑换记录、到账点数和余额结果，不新增流水

#### Scenario: Owner submits the redeemed code again
- **WHEN** 原兑换账号再次提交同一兑换码但使用新的幂等键
- **THEN** 服务端返回“已兑换至当前账号”和原安全结果，不重复增加积分

#### Scenario: Another account submits a used code
- **WHEN** 非原兑换账号提交已使用兑换码
- **THEN** 服务端返回通用不可用结果，不泄露兑换账号、时间、点数或批次内部信息

### Requirement: Enforce code and campaign lifecycle controls
每枚兑换码 MUST 属于一个受权限控制的批次，并 MUST 具有正整数点数、创建时间、可选开始时间、到期时间、状态和全局唯一摘要。批次 SHALL 支持总码数、总点数预算、启用、暂停和撤销；暂停或撤销不得删除既有兑换和账本历史。

#### Scenario: Code is not active yet
- **WHEN** 用户在兑换码开始时间之前提交
- **THEN** 系统不入账并返回通用不可用结果

#### Scenario: Code is expired or revoked
- **WHEN** 用户提交已过期、已撤销或所属批次已暂停的兑换码
- **THEN** 系统不修改码、钱包或会员状态，并提供检查输入或联系客服的安全提示

#### Scenario: Campaign budget is exhausted
- **WHEN** 批次已达到允许的兑换数量或点数预算
- **THEN** 后续兑换原子失败且不得造成批次计数超额或钱包入账

### Requirement: Protect redemption codes as bearer secrets
系统 MUST 使用密码学安全随机源生成足够熵的一次性码，并 MUST 仅持久化带服务端密钥的摘要、码版本和非敏感短标识。完整明文码只 SHALL 在受权限控制的生成交付和用户提交校验时短暂存在，不得进入普通日志、分析事件、错误追踪、客户端存储、页面 URL 或测试 fixture。

#### Scenario: Operations generates a code batch
- **WHEN** 具备兑换码运营权限的人员创建批次
- **THEN** 系统使用安全随机源生成唯一明文码、只保存密钥化摘要，并通过一次性受控导出交付明文

#### Scenario: Redemption request is logged
- **WHEN** 服务端记录兑换请求、失败或指标
- **THEN** 日志只包含请求 ID、结果类别、账号哈希、码版本和安全短标识，不包含完整兑换码或摘要密钥

#### Scenario: User submits a code in the browser
- **WHEN** 前端发送兑换请求并收到结果
- **THEN** 请求使用加密连接，输入不进入 URL 或持久化存储，完成后页面清空明文值

### Requirement: Limit guessing and automated abuse
兑换接口 MUST 要求有效登录会话与跨站请求防护，并 SHALL 按账号和风险来源执行速率限制、连续失败退避和异常检测。达到限制时系统 MUST 在不透露兑换码存在性的情况下拒绝请求，且限流不得修改积分或码状态。

#### Scenario: User repeatedly submits invalid codes
- **WHEN** 同一账号或风险来源在窗口内超过失败阈值
- **THEN** 服务端返回限流结果和可重试时间，不继续执行码查询或账本事务

#### Scenario: Attacker enumerates code variants
- **WHEN** 请求呈现高频、跨账号或连续相似前缀的枚举特征
- **THEN** 系统记录脱敏风险信号、收紧限制或要求额外验证，且不暴露有效、过期和已使用状态差异

### Requirement: Show redeemed points in the existing wallet history
兑换成功后，积分页面 MUST 使用服务端返回的新余额更新当前钱包，并 SHALL 在积分明细展示一条 `redemption_credit` 记录，包括到账点数、兑换时间和安全短标识。兑换积分 MUST 遵循现有整数钱包、消费、预留和会员优先规则，不得创建独立不可消费余额。

#### Scenario: User redeems points while holding a membership
- **WHEN** 有效会员用户成功兑换积分
- **THEN** 积分进入现有钱包并保留，普通回答仍优先使用会员权益且不消耗新积分

#### Scenario: User refreshes after redemption
- **WHEN** 用户兑换成功后刷新或在另一已授权设备打开积分页面
- **THEN** 页面从服务端加载相同余额和兑换流水，不依赖兑换成功页面的本地状态

### Requirement: Restrict issuance and reversal operations
批次创建、码生成、一次性导出、暂停、撤销和兑换积分冲正 MUST 要求独立运营权限并记录不可变审计。普通用户、普通客服和客户端密钥 MUST 无权执行这些操作；冲正 MUST 使用新的负向账本记录，不得修改或删除原兑换流水。

#### Scenario: Unauthorized operator attempts to generate codes
- **WHEN** 不具备兑换码运营权限的账号请求创建或导出批次
- **THEN** 服务端拒绝操作、不生成明文码并记录脱敏安全事件

#### Scenario: Fraudulent redemption is reversed
- **WHEN** 授权运营人员按审核流程确认需要撤销一笔兑换积分
- **THEN** 系统写入关联原兑换记录的冲正流水、保留原历史并防止余额变为不符合钱包规则的状态
