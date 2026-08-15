## ADDED Requirements

### Requirement: Count only normalized indexable content
系统 MUST 对服务端解析并规范化后的可索引 Markdown 正文进行 Token 估算，不得使用原始 PDF、DOCX、DOC 等容器文件的字节数作为 Token 数。当前 `mvp-v1` tokenizer SHALL 使用规范化 UTF-8 正文字节数按每 4 字节向上取整，且所有格式使用同一算法。

#### Scenario: Equivalent PDF and Markdown are quoted
- **WHEN** PDF 与 MD 被解析为相同的规范化可索引正文
- **THEN** 两份新报价显示相同 Token 数、计费单位和积分费用，与各自原始文件大小无关

#### Scenario: PDF contains embedded binary assets
- **WHEN** PDF 包含图片、字体、压缩流或其他不进入规范化正文的二进制内容
- **THEN** 这些容器字节不计入 Token 数和积分报价

#### Scenario: Document has no indexable text
- **WHEN** 文件解析后没有非空的规范化正文
- **THEN** 系统返回无法建立索引的明确错误，且不创建报价、不预留积分或会员额度

### Requirement: Require a server quote before charge confirmation
Web 客户端 SHALL 先上传材料并请求服务端解析报价，再允许用户确认建立索引。最终确认界面 MUST 显示服务端 Token 数、计费单位、预计点数或会员额度来源、预计余额和目录版本；客户端本地估算不得作为确认报价或结算依据。

#### Scenario: User selects a binary document
- **WHEN** 用户选择 PDF、DOCX 或 DOC 文件但尚未完成服务端解析
- **THEN** 页面显示“正在解析并计算报价”或“获取服务端报价”，不得显示按原始文件大小计算的积分数字

#### Scenario: Server quote is ready
- **WHEN** 服务端完成正文解析并生成报价
- **THEN** 页面展示最终服务端报价并启用“确认报价并建立索引”操作

#### Scenario: Parsing or quoting fails
- **WHEN** 服务端无法解析文件或生成报价
- **THEN** 页面展示可操作的失败原因且不允许确认或产生预留

### Requirement: Bind quote confirmation to uploaded content
服务端 MUST 将报价绑定到所属用户、上传意图生成的文档版本、内容指纹、目录版本和 tokenizer 版本。确认请求中的报价缺失、属于其他用户、属于其他文档版本或已失效时 MUST 被拒绝，不得静默创建更高费用的新报价。

#### Scenario: Matching quote is confirmed
- **WHEN** 用户确认仍与当前上传文档版本和内容匹配的服务端报价
- **THEN** 系统仅预留该报价快照对应的积分或会员额度并提交索引任务

#### Scenario: Quote belongs to another document
- **WHEN** 确认请求携带同一用户另一文档版本的报价
- **THEN** 系统拒绝请求且不预留任何积分或会员额度

#### Scenario: Legacy client omits quote
- **WHEN** 旧客户端直接确认知识材料但没有携带服务端报价 ID
- **THEN** 服务端按当前上传内容解析并生成安全报价，但在费用高于客户端可能已展示的估算时拒绝静默确认并要求客户端重新展示报价

### Requirement: Reuse the normalized quote artifact
服务端 SHALL 将预报价阶段生成的规范化 Markdown 保存为该文档版本的受控产物，并在正式索引及无内容变化的重试中复用。正文和对象存储地址不得写入报价或计费日志。

#### Scenario: Confirmed PDF enters indexing
- **WHEN** PDF 的服务端报价已生成且用户确认建立索引
- **THEN** 正式处理任务复用同一文档版本的规范化 Markdown，不再次调用远程 PDF 解析器

#### Scenario: Same version is retried
- **WHEN** 向量化失败后用户重试未改变内容的同一文档版本
- **THEN** 系统按缓存的规范化正文重新生成或复用报价，并避免按原始文件大小计费
