## Context

OfferSteady 当前的资料库原型已经区分了简历、职位 JD 和知识库三个分区，前端也已经明确展示支持的文件格式 `PDF / DOCX / DOC / TXT / MD`。但服务端 `apps/backend` 仍停留在占位接口阶段：`resume`、`job_description`、`knowledge` 只有 `501` 风格的占位响应，`storage` 端口也只返回一个 placeholder URI。

这意味着目前“资料上传”仍然只是界面原型，而不是一条真实可用的产品链路。要把它推进到 MVP 的下一步，我们至少要解决下面几件事：

- 文件怎么安全地进入对象存储，而不是经过浏览器保存长期密钥
- 简历、JD、知识资料如何复用一套上传与状态机制，同时保留各自类型边界
- 上传成功后怎样进入“待处理 / 处理中 / 就绪 / 失败”的后续状态流
- 前端怎样在不改变现有页面结构的情况下接入真实上传流程
- 后续解析、RAG、面试资料选择怎样复用这条链路，而不是再单独造一套

结合仓库当前工程基线，这次设计必须与以下事实保持一致：

- Web 端继续基于 `React + TypeScript + Vite`
- 正式后端主线是 `FastAPI`
- 敏感资料不把云存储密钥下发给客户端
- 文件存储使用阿里云 OSS
- 解析、索引、检索与生成保持可替换适配器
- 不改变当前资料页、准备页和实时面试页的既有原型结构

## Goals / Non-Goals

**Goals:**

- 为资料库文件上传设计一条适合 MVP 的完整链路：前端发起、服务端授权、直传 OSS、完成确认、元数据登记、后续处理状态流转
- 在服务端建立统一的资料上传域模型和模块边界，覆盖简历、JD 文件和知识资料文件
- 让前后端共享同一份受支持文件类型约束 `pdf/docx/doc/txt/md`
- 为后续解析、知识索引 / RAG、面试准备资料选择和删除治理预留稳定扩展点
- 明确 JD 粘贴文本和文件上传的边界，避免把两类创建方式混为一谈

**Non-Goals:**

- 不在本变更中实现完整的 PDF/DOCX/DOC 解析逻辑
- 不在本变更中完成向量索引、检索召回、模型调用或实时回答
- 不在本变更中确定最终数据库选型或任务队列产品
- 不在本变更中实现分片大文件断点续传；MVP 先按单文件上传设计
- 不改变现有页面信息架构，不新增与上传无关的产品流程

## Decisions

### 1. Use a backend-issued upload intent plus direct-to-OSS upload

MVP 采用“两阶段上传”：

1. 客户端调用 FastAPI 的上传意图接口
2. 服务端校验资料类型、文件格式、用户身份和上传约束后，返回短时有效的 OSS 上传参数
3. 客户端使用这些参数直接把文件传到 OSS
4. 客户端调用完成确认接口
5. 服务端登记资料来源记录并触发后续处理

这样做的原因是：

- 浏览器无需持有长期 OSS 凭证
- 后端不需要代理整份文件流量，降低应用层带宽压力
- 未来接入桌面端、移动端或大一点的知识材料时更容易扩展

替代方案是“所有文件先传到 FastAPI，再由后端转存 OSS”。这个方案实现直观，但会让应用服务承担文件中转、重试、超时和资源消耗压力；对你这个后续会有简历、JD、截图、知识资料的产品来说，可扩展性较差，所以不作为 MVP 主路径。

### 2. Model uploads as one shared material-ingestion domain with typed material kinds

虽然前端产品上有三类资料，但上传基础设施应该尽量统一。设计上引入一套共享上传域模型：

- `material_kind`: `resume | job_description | knowledge`
- `upload_method`: `file | pasted_text`
- `upload_intent`: 一次短时有效的上传授权
- `material_source`: 用户资料库中的一个来源记录
- `processing_state`: `pending_upload | uploaded | queued | processing | ready | failed | deleted`

这套模型的好处是：

- 简历、JD 文件、知识资料文件都走同一条上传链路
- 准备页和资料页可以围绕同一套状态语义工作
- 后续解析器、索引器、删除器不需要分别理解三套不同上传协议

替代方案是为 `resume`、`job_description`、`knowledge` 各自设计完全独立的上传接口和状态模型。这样短期看似更快，但很容易造成状态语义不一致，例如某一类叫 `uploaded`、另一类叫 `pending_parse`，最后前端展示和准备页禁选逻辑都会变复杂。

### 3. Keep one canonical format registry across frontend and backend

这次上传能力必须复用一份统一的格式定义，而不是前端写一套 `accept`，后端再手写另一套判断。推荐做法：

- 在共享协议层维护 canonical format registry，至少包含扩展名、展示名、可接受 MIME、适用资料类型
- 前端上传控件从这份 registry 派生 `accept` 和错误提示
- 后端上传意图接口和完成确认接口使用同一份 registry 校验

当前规范统一支持：

- `pdf`
- `docx`
- `doc`
- `txt`
- `md`

替代方案是继续让前端只控制 `accept`，后端只凭文件名后缀做松散判断。这样容易造成“前端能选、后端拒绝”或“前端不能选、后端其实支持”的体验割裂。

### 4. Separate upload completion from material readiness

文件到达 OSS 只代表“对象已写入”，不代表“资料已可用于面试”。所以服务端必须把“上传完成”与“处理完成”拆开：

- `upload_intent created`
- `oss object uploaded`
- `material_source registered`
- `processing queued`
- `processing ready/failed`

资料页可以在上传完成后立即显示这条来源，但必须标成“待处理 / 处理中”，准备页则只允许 `ready` 状态进入本场资料清单。

替代方案是上传成功后立刻把资料显示为可用。这个方案会让用户误以为系统已经完成解析、索引和校验，不适合你当前已经明确区分“可用于面试”和“处理中/失败”的产品逻辑。

### 5. Keep JD pasted text as a sibling path, not a fake file upload

职位 JD 目前除了文件上传，还支持直接粘贴文本。这条能力应当独立成“文本创建”接口，而不是为了统一而强行在浏览器把文本生成临时文件再走 OSS。

原因是：

- 用户心智更清楚：粘贴文本不是上传文件
- 服务端可以针对文本长度、编码和清洗做更直接的处理
- 不会额外引入无意义的 OSS 对象与上传失败重试复杂度

不过它仍然应该复用同一套 `material_source`、状态和所有权边界，避免成为资料库里的“第二类 JD”。

替代方案是把粘贴文本先转换为 `.txt` 再上传到 OSS。这样能让底层更统一，但会让交互与审计语义都显得别扭，MVP 没必要这么做。

### 6. Introduce an explicit storage adapter for Aliyun OSS in the backend

当前 `app/ports/storage.py` 只有 placeholder。后续实现时应在 `apps/backend` 内形成明确边界：

- `FileStoragePort`
  - `create_upload_intent(...)`
  - `confirm_uploaded_object(...)`
  - `delete_object(...)`
  - `get_internal_read_url(...)` 或等效能力
- `AliyunOssStorageAdapter`
  - 负责 bucket、region、endpoint、prefix、policy/signature

这样后续解析服务只依赖抽象端口获取对象读取权限，而不是直接耦合 OSS SDK。

替代方案是先在 `resume.py`、`job_description.py`、`knowledge.py` 里分别直接写 OSS 调用。这会把对象存储逻辑散落到多个业务模块中，后续截图、导出、删除也会重复同样的问题。

### 7. Use deterministic object-key conventions with per-user isolation

对象键建议按资料类型和用户作用域分层，例如：

```text
materials/{user_id}/{material_kind}/{source_id}/{revision}/{sanitized_filename}
```

配套要求：

- 服务端生成对象键，客户端不得自行决定最终 key
- 文件名只用于展示或附加，不作为权限边界
- 版本替换时创建新 revision，旧 revision 根据策略保留或标删除

这样做的好处是：

- 便于后续删除、替换、审计和问题排查
- 能和“同一个资料多版本”模型自然对齐
- 避免不同用户或不同资料类型之间对象路径混淆

替代方案是只按时间戳生成随机对象名。虽然简单，但后续在资料替换、版本回溯和故障定位上会比较难管理。

### 8. Make processing asynchronous behind a material-processing boundary

文件上传完成后，不在请求链路内同步执行完整解析。MVP 设计成：

- 完成确认接口只做轻量校验与状态登记
- 后续由 `material processing` 边界异步消费
- 对简历/JD：生成结构化提取结果或最小可检索文本
- 对知识资料：生成切片、索引或后续 RAG 原料

这样一来，上传链路稳定、页面响应更快，也更符合当前原型里已经存在的“处理中 / 可用于面试 / 失败”状态表达。

替代方案是用户点上传后同步等待解析完成再返回。对于文档类资料，这会让接口耗时和失败恢复都变得不友好。

## Risks / Trade-offs

- [Risk] 直传 OSS 会让前端上传状态机更复杂 → Mitigation: 把流程固定为“申请意图 → 直传 → 完成确认”三步，并通过统一 adapter 封装
- [Risk] `doc` 文件的 MIME 与解析兼容性可能不稳定 → Mitigation: 先把 `doc` 支持定义为“允许上传 + 后续处理可能失败”，在状态上诚实暴露失败而不是提前承诺解析质量
- [Risk] 如果上传成功但完成确认失败，OSS 里会残留未登记对象 → Mitigation: 为上传意图设置过期和后台清理任务，定期删除未完成确认的孤儿对象
- [Risk] 文件格式前后端约束不一致会造成体验割裂 → Mitigation: 维护一份 canonical registry，并在测试中覆盖前后端一致性
- [Risk] 后续知识库索引计费与上传耦合过深 → Mitigation: 本设计只解决上传和资料登记，不把“上传成功”直接等同于“扣点成功”或“索引成功”
- [Risk] OSS 路径和用户标识暴露不当会增加隐私面 → Mitigation: 对外只返回必要上传参数，不在客户端或普通日志暴露内部对象定位信息

## Migration Plan

1. 在 `apps/backend` 中先把上传能力从 placeholder 模块提升为明确接口骨架，补齐 schema、storage port 和配置项。
2. 在前端通信层引入资料上传 adapter，保持页面结构不变，只把当前本地模拟上传替换为真实 API 流程。
3. 先实现简历、JD 文件、知识资料文件三类统一上传链路，再保留 JD 文本粘贴为并行创建路径。
4. 在服务端把上传完成后的资料状态统一接入现有资料列表查询与准备页读取模型。
5. 后续再以单独变更接入真实解析、索引和 RAG，不在本次上传链路实现中一并塞入。

回滚策略：

- 若 OSS 直传集成出现问题，可临时保留原型模式作为前端演示回退路径
- 已新增的资料上传 API 应返回明确失败，而不是伪造成功状态
- 不回滚既有资料页、准备页和实时工作台的 UI 结构

## Open Questions

- MVP 是否需要在第一版就支持 OSS 分片上传，还是先以常见简历/JD/知识资料大小的单对象上传为准？
- pasted JD 文本最终是否也需要在服务端归档到对象存储以统一审计，还是先保存在事务存储即可？
- 资料删除时，是否立即物理删除 OSS 对象，还是先软删除资料记录并异步清理对象？
- 后续解析 / 索引异步任务准备采用什么执行方式：FastAPI 后台任务、独立 worker，还是消息队列？
- 不同资料类型是否需要不同的大小限制与失败文案，例如知识资料大于简历文件时给出不同提示？
