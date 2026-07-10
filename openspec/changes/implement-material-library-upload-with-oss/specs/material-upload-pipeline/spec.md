## ADDED Requirements

### Requirement: Issue a server-authorized upload intent before any file reaches OSS
系统 MUST 在简历、职位 JD、知识资料的文件上传开始前，由可信服务端创建一次上传意图，并返回与当前账号、资料类型、文件名、内容类型和短时有效期绑定的 OSS 上传参数。客户端 MUST NOT 自行拼接长期可写对象路径或持有长期 OSS 密钥。

#### Scenario: User uploads a resume file
- **WHEN** 用户在资料页选择一份 `PDF/DOCX/DOC/TXT/MD` 简历文件并点击上传
- **THEN** 客户端先向服务端申请简历上传意图，再使用返回的短期 OSS 参数执行上传，而不是直接写死对象存储地址

#### Scenario: Upload intent expires
- **WHEN** 客户端在上传意图过期后仍尝试复用原参数上传
- **THEN** 系统拒绝该次完成确认，并要求客户端重新申请新的上传意图

### Requirement: Enforce the same supported file formats on both client and server
系统 MUST 对简历、JD 文件和知识资料文件统一支持 `PDF、DOCX、DOC、TXT、MD`，并 MUST 在前端选择阶段和服务端上传意图创建阶段同时校验扩展名与可接受内容类型。任一不受支持的文件 MUST 在进入 OSS 持久化前被拒绝，且错误信息 SHALL 明确说明当前支持范围。

#### Scenario: User selects an unsupported file type
- **WHEN** 用户选择 `PNG`、`ZIP` 或其他不在支持列表中的文件
- **THEN** 前端阻止继续上传，并向用户展示当前仅支持 `PDF、DOCX、DOC、TXT、MD`

#### Scenario: Client bypasses the UI restriction
- **WHEN** 客户端绕过前端限制，向上传意图接口提交不受支持的文件扩展名或内容类型
- **THEN** 服务端拒绝签发上传意图，且不会创建可写 OSS 参数

### Requirement: Complete upload only after the server confirms the object and registers a material source
文件成功写入 OSS 后，客户端 MUST 调用完成确认接口；服务端 MUST 校验该对象属于当前上传意图、属于当前账号并符合预期元数据，然后再创建或更新资料来源记录。资料来源在完成确认前 MUST NOT 出现在可用于面试的资料列表中。

#### Scenario: Upload finishes successfully
- **WHEN** 客户端把文件上传到 OSS 并调用完成确认接口
- **THEN** 服务端登记一条属于对应资料类型的来源记录，并把状态设为“已上传待处理”或等效的非就绪状态

#### Scenario: File upload is interrupted before completion
- **WHEN** 客户端未完成 OSS 上传或未调用完成确认接口
- **THEN** 系统不会把该文件显示为可选资料，也不会把它标记为可用于面试

### Requirement: Material processing state must remain explicit after upload
系统 MUST 为资料上传后的处理链路维护明确状态，至少覆盖“待上传 / 上传中 / 已上传待处理 / 处理中 / 就绪 / 失败 / 已删除”中的产品等效状态。准备页与资料页只可把 `就绪` 状态的资料视为可选来源；上传成功但尚未处理完成的资料 MUST 保持不可用于新面试。

#### Scenario: Uploaded knowledge file is still processing
- **WHEN** 用户上传一份知识资料且后续索引尚未完成
- **THEN** 资料页展示处理中状态，准备页禁止把它加入本场允许清单

#### Scenario: Material processing fails
- **WHEN** 服务端后续解析或索引失败
- **THEN** 系统把资料状态标记为失败，并允许用户在资料管理页重新上传、替换或删除，而不是静默当作可用资料

### Requirement: Keep JD text creation separate from the OSS file-upload pipeline
系统 MUST 将“粘贴 JD 文本”视为独立于 OSS 文件上传的资料创建路径。该路径 SHALL 复用同一套资料所有权、状态和后续处理边界，但 MUST NOT 要求用户先生成 OSS 文件上传意图。

#### Scenario: User pastes JD text
- **WHEN** 用户在职位 JD 分区直接粘贴文本并提交
- **THEN** 系统通过文本创建接口登记一条 JD 类型来源，并进入与 JD 文件一致的后续处理状态流

#### Scenario: User opens the JD upload dialog
- **WHEN** 用户在职位 JD 分区查看添加说明
- **THEN** 系统分别说明“支持上传 PDF、DOCX、DOC、TXT、MD”和“也支持直接粘贴 JD 文本”，而不是把两者描述成同一条 OSS 上传能力
