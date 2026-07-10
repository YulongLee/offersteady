## ADDED Requirements

### Requirement: Create an order before payment
系统 MUST 在展示对应商户收款信息前创建包含唯一订单号、商品快照、应付金额、渠道和过期时间的订单。

#### Scenario: User chooses WeChat payment
- **WHEN** 用户为一个已上架商品选择微信支付
- **THEN** 系统创建待支付订单并展示该订单适用的微信商户收款信息和订单号

#### Scenario: Product changes after order creation
- **WHEN** 待支付订单创建后商品价格发生变化
- **THEN** 该订单继续使用创建时价格直到过期，且新订单使用新价格

### Requirement: Accept payment proof for manual review
MVP SHALL 允许用户上传微信或支付宝付款截图、填写交易参考信息和付款时间，并 MUST 将订单置为待人工审核而不是自动到账。

#### Scenario: User submits a valid-format proof
- **WHEN** 用户为自己的待支付订单上传受支持的截图和交易信息
- **THEN** 系统加密保存凭证、计算重复检测摘要并将订单标为 `under_review`

#### Scenario: OCR appears to match
- **WHEN** OCR 提取的金额和订单金额一致
- **THEN** 系统只把结果作为审核辅助，仍不得在未核对商户账单时发放权益

### Requirement: Verify payment against merchant records
获授权审核者 MUST 核对商户账单中的金额、时间、交易号、渠道和订单，并 SHALL 通过幂等事务确认或拒绝订单。

#### Scenario: Reviewer confirms payment
- **WHEN** 审核者确认商户账单存在唯一匹配交易
- **THEN** 系统将订单标为已支付并且只发放一次对应积分或会员权益

#### Scenario: Duplicate proof is submitted
- **WHEN** 同一截图、交易号或商户交易被用于第二个订单
- **THEN** 系统阻止自动通过、标记风险并要求人工处理

#### Scenario: Reviewer rejects proof
- **WHEN** 付款金额不符、交易不存在或凭证无法核实
- **THEN** 系统记录不含付款敏感正文的拒绝原因并允许用户联系售后或重新提交

### Requirement: Provide transparent order states
系统 SHALL 让用户查看待付款、已提交、审核中、已支付、已拒绝、已过期、退款中和已退款状态，并 MUST 显示下一步操作。

#### Scenario: Review is pending
- **WHEN** 用户打开审核中的订单
- **THEN** 页面展示提交时间、预计处理说明、订单号和客服入口，不提前显示权益已到账

### Requirement: Integrate official merchant payment adapters
系统 SHALL 为微信支付和支付宝正式商户接入提供服务端下单、支付通知、主动查单、退款和对账适配器，并 MUST 只依据验证后的服务端支付结果自动发放权益。

#### Scenario: Browser reports payment success
- **WHEN** 浏览器或客户端声称支付成功
- **THEN** 系统主动查单或等待验证后的支付通知，不能仅依据客户端状态入账

#### Scenario: Duplicate payment notification arrives
- **WHEN** 支付平台重复发送同一交易通知
- **THEN** 系统返回幂等成功结果且不重复发放权益

### Requirement: Protect payment evidence
系统 MUST 限制付款截图格式和大小、执行恶意文件检测、加密存储、控制审核访问并按公布期限删除，不得把截图、交易号或付款人信息写入普通日志。

#### Scenario: Unauthorized staff requests a proof
- **WHEN** 没有订单审核权限的人员尝试查看付款凭证
- **THEN** 系统拒绝访问并记录安全审计事件

### Requirement: Provide customer-service WeChat access
收费页、订单详情和余额不足页面 SHALL 提供由服务端配置的客服微信二维码、可复制微信号、服务时间和携带订单号的咨询说明。

#### Scenario: User contacts support about an order
- **WHEN** 用户从订单详情点击联系客服
- **THEN** 系统展示当前受控客服微信信息并提示用户提供订单号而不是发送完整付款截图到公开渠道

### Requirement: Audit privileged billing actions
系统 MUST 对审核通过、审核拒绝、人工积分调整、会员调整和退款操作记录操作人、时间、原因、前后状态和关联订单，普通客服 SHALL 无权直接修改余额。

#### Scenario: Support agent attempts a direct balance edit
- **WHEN** 只有普通客服权限的账号尝试修改用户积分
- **THEN** 系统拒绝操作并要求进入受控审批流程
