## Why

当前资料库、OSS、MinerU、向量索引和面试会话之间仍存在体验断裂：用户上传资料后，创建面试时绑定资料偏慢，且回答阶段是否真正使用资料不够稳定、可解释。现在需要把资料上传后的重处理前移到资料库后台，将创建面试简化为选择已可用能力，并确保回答只使用本场确认快照。

## What Changes

- 将资料库定义为资料能力生产中心：上传完成后由后端异步完成 OSS 原文保存、MinerU 转 Markdown、processed artifacts 保存、chunk 生成、embedding、向量索引和数据库可用性记录。
- 将创建/准备面试定义为轻量绑定流程：只允许选择后端已标记为可用的简历、JD 和知识库资料，确认时不再同步执行重型 OSS 扫描、MinerU 转换或向量构建。
- 增加资料可用性状态模型：区分 uploaded、processing、artifact-ready、indexed、selectable、failed、stale、deleted 等状态，并向资料库页和准备页展示一致状态。
- 明确前端、后端数据库与 OSS 的同步边界：前端资料列表以后端数据库为事实源；数据库必须记录 OSS object/artifact 状态；新增、删除和后台校验都要同步更新资料状态。
- 明确 OSS 与数据库同步校验：资料处理完成时必须校验关键 OSS artifacts；准备页使用数据库中的 verified/selectable 结果；回答前仍做 fail-closed 读取校验，发现失效则显式降级提示。
- 固化面试资料快照：创建面试确认资料后，后端保存 document/version 级快照；实时回答和截图回答只使用该快照，不自动读取资料库最新未确认变化。
- 优化回答 grounding 展示：简历/JD 作为固定 Prompt 上下文，知识库作为 RAG 检索上下文，回答结果展示固定资料、知识库命中和不可用来源。
- 保留当前产品原型结构和开发范式，不新增复杂资料编辑器，不允许客户端直接访问 OSS、Embedding、Rerank 或 Chat Provider 密钥。

## Capabilities

### New Capabilities
- `material-capability-pipeline`: 资料上传后由后端异步转换为可被面试使用的能力，包括 OSS artifacts、Markdown、chunks、向量索引、数据库状态和可选性。
- `session-material-grounding`: 面试会话确认资料快照、回答阶段资料装配、RAG 检索边界和资料来源溯源。

### Modified Capabilities
- `streamlined-interview-entry`: 准备页从后端资料库状态选择资料，确认时执行轻量后端绑定并阻止不可用资料进入面试。

## Impact

- `apps/backend`: Document Service、Document Processing、MinerU adapter、Embedding pipeline、Material availability、Session Service、Chat Service、Screenshot Answer Service、Postgres persistence、OSS object key conventions。
- `apps/web`: 资料库状态展示、准备页资料选择与确认状态、实时回答来源展示、资料不可用提示。
- `packages/protocol`: 资料状态、selectable/unavailable reason、session material snapshot、answer provenance 和 RAG/fixed context 字段。
- `ai/prompts`: 明确简历/JD 固定上下文、知识库 RAG 上下文、无资料或资料不可用时不得编造。
- `ai/evals`: 增加资料绑定后回答必须引用资料、知识库命中、资料不可用降级和无资料不编造案例。
- 数据与隐私：资料全文、Prompt、embedding 和供应商 payload 不暴露给客户端；日志只记录安全摘要、ID、状态、耗时和错误码。
