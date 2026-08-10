## ADDED Requirements

### Requirement: 支付宝密钥输入兼容
系统 MUST 接受完整 PEM 或支付宝工具直接复制的无头尾 Base64 RSA 密钥，并在加密存储前规范化为可解析的 PEM。

#### Scenario: 保存直接复制的应用私钥
- **WHEN** 管理员提交无 PEM 头尾但可解析为 RSA 私钥的 Base64 文本
- **THEN** 系统将其规范化为 PKCS#8 PEM、通过配置校验并只加密存储规范化结果

#### Scenario: 保存直接复制的支付宝公钥
- **WHEN** 管理员提交无 PEM 头尾但可解析为 RSA 公钥的 Base64 文本
- **THEN** 系统将其规范化为 SubjectPublicKeyInfo PEM并通过配置校验

#### Scenario: 保持完整 PEM 兼容
- **WHEN** 管理员提交有效的完整 PEM RSA 私钥和公钥
- **THEN** 系统继续接受并规范化这些密钥

### Requirement: 支付宝密钥类型安全
系统 MUST 使用密码学解析验证支付宝密钥，并 MUST 拒绝损坏内容、非 RSA 密钥和证书正文，且不得在响应或日志中返回密钥内容。

#### Scenario: 拒绝错误密钥类型
- **WHEN** 管理员把 EC 密钥、证书或不可解析文本提交到支付宝密钥字段
- **THEN** 系统保持渠道为草稿并返回不含密钥正文的字段级错误

#### Scenario: 重新校验已保存的 Base64 草稿
- **WHEN** 渠道已加密保存可解析的 Base64 密钥草稿且管理员不替换密钥再次保存
- **THEN** 系统规范化已有密钥并允许配置进入可启用状态
