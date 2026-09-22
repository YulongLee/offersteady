## ADDED Requirements

### Requirement: Uploaded resume processing reaches a visible terminal state
系统 MUST 在简历上传后持续查询处理状态，直到文档进入 ready、failed、deleted 或 disabled 等终态；超过等待上限时必须显示仍在后台处理，而不是显示解析失败。

#### Scenario: Slow PDF finishes after the initial wait window
- **WHEN** 后端 PDF 解析耗时超过 17 秒但在 90 秒内完成
- **THEN** Web 端继续刷新并显示“可用于面试”，不要求用户重新上传

#### Scenario: Processing exceeds the bounded wait window
- **WHEN** 文档在 90 秒内仍未进入终态
- **THEN** Web 端停止本轮轮询并提示用户稍后刷新，后台任务继续运行

### Requirement: Retryable parser failures are durable and bounded
系统 MUST 将 MinerU 无效结果、对象存储临时读取失败和供应商暂时不可用识别为可恢复错误，最多重试两次；每次重试必须使用原任务身份并保持幂等。

#### Scenario: MinerU returns an invalid result
- **WHEN** 解析器返回空结果、缺失必需字段或 `parser_invalid_result`
- **THEN** 任务记录安全错误码并进入可调度重试状态，未超过上限时重新执行解析

#### Scenario: Retry limit is exhausted
- **WHEN** 同一文档的可恢复解析失败达到最大重试次数
- **THEN** 处理任务、持久化作业和文档统一进入失败终态，并向 Web 返回可操作的失败提示

### Requirement: Non-retryable document failures fail closed
系统 MUST 对不支持的格式、空文档、无法解码的文本、文档已删除等不可恢复情况直接标记失败，不得无限重试或标记为 ready。

#### Scenario: Encrypted or invalid PDF cannot be parsed
- **WHEN** 解析器确认文件不可读取或内容为空
- **THEN** 文档进入失败状态，页面说明需要重新上传可读取文件，且不产生可用的空解析结果

### Requirement: Processing state is consistent across persistence layers
系统 MUST 保证处理任务、持久化处理作业和文档状态在成功、失败和删除路径上最终一致；不得长期出现任务为 QUEUED、作业为 failed、文档仍为 processing 的组合。

#### Scenario: Background task completes successfully
- **WHEN** PDF 已生成有效标准化 Markdown 并完成后续处理
- **THEN** 任务为 COMPLETED、处理作业为 succeeded、文档为 ready

#### Scenario: Document is deleted during processing
- **WHEN** 用户删除仍在处理的简历
- **THEN** 任务和作业以 document_deleted 结束，文档不可再次被选择，且不会继续重试

### Requirement: Sensitive document content is excluded from diagnostics
系统 MUST 仅记录任务标识、阶段、耗时和安全错误码，不记录简历全文、模型供应商原始响应或对象存储凭证。

#### Scenario: Parser failure is logged
- **WHEN** MinerU 或 OSS 处理失败
- **THEN** 日志包含安全错误码和耗时，但不包含简历文本或供应商原始 payload
