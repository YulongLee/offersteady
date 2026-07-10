## Context

OfferSteady 当前已经具备一套较完整的 Web 原型，前端实现基于 React + TypeScript + Vite，页面结构和交互已经覆盖首页、登录、资料库、计费页、准备页和实时面试工作台。与此同时，仓库中也存在一个以 TypeScript 模块为主的 `apps/api` 原型服务，用于验证部分协议、账本和业务契约，但这套服务还不是你现在想要的正式 MVP 后端方向。

你已经明确了第一阶段的目标：不改变产品原型的页面结构和交互，不提前实现业务逻辑，而是先确定整体技术架构与模块划分，搭起 FastAPI 后端基础工程和 React 与后端的通信框架，并为上传简历、上传 JD、知识库 / RAG、实时回答、截图回答等能力预留落位点。

这意味着第一阶段是一次“工程收束”而不是“功能上线”：

- 对前端来说，重点是把现有原型从本地夹具为主，过渡到可连接真实后端的服务边界
- 对后端来说，重点是确立 FastAPI 作为正式服务端框架，并建立清晰的模块、配置和路由骨架
- 对共享层来说，重点是让前后端围绕统一契约对接，而不是让每个页面和每个接口各自生长

这份设计还需要和刚完成的 `define-mvp-technical-architecture` 保持一致：Web 仍是主要产品入口，桌面伴随程序是后续独立客户端；实时与异步处理分离；AI 与外部能力通过可替换适配器接入；敏感数据维持最小化保存边界。

## Goals / Non-Goals

**Goals:**

- 把现有原型收束为可继续开发的 MVP 第一阶段工程底座
- 在不改变现有前端页面结构和交互的前提下，引入 React 到后端的统一通信层
- 以 FastAPI 确立后端基础工程、路由骨架、配置体系和功能模块边界
- 为简历、JD、RAG、实时回答、截图回答、会话编排等后续能力预留清晰的前后端落位点
- 明确当前 TypeScript 原型服务与未来 FastAPI 正式服务的迁移方向

**Non-Goals:**

- 不实现任何真实业务逻辑，包括文件上传处理、向量索引、模型调用、实时流式回答和截图分析
- 不在本阶段完成数据库建模、对象存储接入、真实鉴权、支付回调或生产级部署
- 不重做原型 UI，不新增页面信息架构或新的产品流程
- 不在本阶段确定最终 AI 供应商、RAG 存储引擎或生产实时音频方案

## Decisions

### 1. Keep the existing React prototype as the presentation baseline

第一阶段直接沿用现有 `apps/web` 作为 MVP Web 端展示层基线，不重做页面，不替换 React 技术栈，也不重排组件结构。我们只会在页面背后的数据访问方式上引入新的通信抽象，例如 API client、repository / adapter、请求状态与错误归一层。

这样做的原因很简单：当前原型的最大价值在于已经把产品体验跑通了，而第一阶段的任务是让它变成“能继续接业务”的工程，不是再回头重做设计。替代方案是趁机大规模重构前端组件或换框架，但那会把“工程搭底座”和“重做产品体验”混在一起，风险很高。

### 2. Use FastAPI as the formal MVP backend foundation

服务端正式方向切到 FastAPI，并把第一阶段的后端目标限定为一个“可启动、可扩展、可挂接模块”的基础应用。推荐将 `apps/api` 调整为 FastAPI 服务主目录，至少包含：

- 应用入口与应用工厂
- `api/v1` 路由层
- `core` 配置 / 日志 / 异常处理
- `deps` 或等效依赖注入层
- `modules` 或按功能域拆分的路由与服务占位
- 基础测试与启动文档

选择 FastAPI 而不是继续沿用现有 TypeScript 服务，是因为你已经明确指定第一阶段后端要走 FastAPI，同时这也更适合后续文件上传、异步任务、AI 编排和 Python 生态集成。替代方案是保留 TypeScript 原型服务继续扩展，这会让现在的目标与后续真实实现方向再次分叉。

### 3. Separate transport contracts from implementation logic

前后端之间保持一层稳定契约。现有 `packages/protocol` 已经承载了一部分前端与原型服务共享类型，第一阶段需要决定哪些契约继续保留为前端友好的共享模型，哪些由 FastAPI 通过 OpenAPI / Pydantic schema 对外提供。无论最终细节怎样，页面组件都不应该依赖后端内部实现细节。

推荐的做法是：

- 前端保留稳定的领域类型与 UI 侧错误模型
- FastAPI 侧使用明确的 request / response schema
- 两边通过通信层做必要映射，而不是直接让视图消费裸 HTTP 结果

替代方案是页面直接使用 fetch 返回值并在每个组件里各自解析，这在第一阶段会很快失控。

### 4. Introduce a backend communication layer that supports both fixture mode and API mode

因为第一阶段不实现真实业务逻辑，前端不能在接入 FastAPI 后立刻失去原型可演示性。所以通信层要支持双模式：

- Fixture / Prototype Mode：继续使用现有合成状态、夹具适配器和本地演示数据
- API Mode：通过统一 API client 访问 FastAPI 基础服务和占位接口

页面组件只依赖统一 adapter / service 接口，不感知当前底层是夹具还是 HTTP。这样一来，后续某个模块即使还没做完，也不会阻塞整个原型继续展示。

替代方案是一次性把所有页面强制切到真实 API，再等待每个接口完成；这会让第一阶段很难保持产品原型的完整可用性。

### 5. Pre-split feature domains before implementing their logic

第一阶段先把未来最重要的能力按域拆出来，不做逻辑但要给出位置：

- `resume`：简历上传与资料元信息
- `job_description`：JD 上传与资料元信息
- `knowledge`：知识库 / RAG 数据源与索引占位
- `live_answer`：实时回答入口与会话回答任务占位
- `screenshot_answer`：截图任务入口与结果占位
- `session`：面试准备、会话状态与恢复占位

前端和 FastAPI 都按这些域建立目录或模块，避免后面业务一来就全部塞进 `App.tsx`、`api-client.ts` 或单一 `main.py`。替代方案是先只做一个通用“interview”大模块，但这会让上传、检索、截图、会话状态继续纠缠在一起。

### 6. Keep placeholder behavior explicit and uniform

本阶段不做业务逻辑，就必须把“未实现”当作正式行为来设计。也就是说：

- FastAPI 预留接口返回结构化占位结果或统一未实现错误
- 前端通信层能稳定识别这种结果
- 页面继续维持现有 empty / pending / error / success 样式能力，但不伪造成功业务数据

这能避免“看起来接口已经通了，其实返回的是假业务结果”的混淆。替代方案是随手返回模拟成功内容，但那会让第二阶段很难看清哪些能力真的完成了。

### 7. Defer storage and AI integrations behind empty ports

为了给后续上传和 AI 功能铺路，第一阶段会预留扩展点，但不接实物：

- 文件存储端口
- 资料解析端口
- 向量检索 / RAG 端口
- 回答生成端口
- 截图分析端口
- 实时事件 / 流式输出端口

FastAPI 服务模块只依赖这些抽象位置或占位 service，不在当前阶段直接引入具体云服务 SDK、模型 SDK 或向量数据库。替代方案是直接为某个供应商写死接口，这与前面确定的“可替换适配器”原则冲突。

## Risks / Trade-offs

- [Risk] 把后端方向从 TypeScript 原型切到 FastAPI，会出现一段迁移期内双轨理解成本
  Mitigation: 在设计和任务中明确 TypeScript `apps/api` 是原型参考，FastAPI 是正式第一阶段主线，并把迁移范围限定在基础工程而非功能重写

- [Risk] 保持 UI 不变会限制一部分更适合真实后端的数据状态表达
  Mitigation: 第一阶段优先保护产品验证资产，只在通信层和状态映射层处理差异，不用页面重构来解决工程问题

- [Risk] 双模式通信层会增加一点抽象成本
  Mitigation: 用统一 adapter 接口换取原型可演示性和后续 API 接入弹性，这个成本在 MVP 早期是值得的

- [Risk] 占位接口太多，团队可能误以为功能已经“差不多完成”
  Mitigation: 占位响应必须显式标注未实现状态，文档和任务里也要把基础工程与业务实现分开

- [Risk] 先预留模块不做业务，短期看产出不如直接写功能明显
  Mitigation: 用后续上传、RAG、截图和实时回答的接入效率来证明这一步的价值，避免每个功能都重复搭底座

## Migration Plan

1. 先确认这份变更作为 MVP 第一阶段工程实施基线，与 `define-mvp-technical-architecture` 一起构成“架构 + 工程底座”参考。
2. 在 apply 阶段保留 `apps/web` 的页面结构和交互，实现前端通信层抽象、环境配置和双模式数据访问。
3. 在 apply 阶段建立 FastAPI 工程骨架，并按功能域挂好基础路由和占位服务。
4. 将当前 TypeScript `apps/api` 中仍有参考价值的契约、错误形状和原型行为整理迁移到共享协议或文档，而不是继续把它视为正式服务端主线。
5. 后续上传简历、上传 JD、RAG、实时回答、截图回答等能力分别通过新的实现型 change 接入这些已预留模块。

回滚策略：如果第一阶段工程底座方向需要调整，优先回滚新增的工程骨架和通信抽象，不回滚现有前端页面结构与原型体验资产。

## Open Questions

- FastAPI 第一阶段是否直接占用 `apps/api` 目录，还是需要单独新建 `apps/backend` 再逐步迁移？
- 共享协议未来是继续由 `packages/protocol` 主导，还是逐步以 FastAPI 生成的 schema 为主、前端再做类型映射？
- 第一阶段是否需要同时补上基础开发命令，例如 Web 与 FastAPI 的联合启动脚本？
- 桌面伴随程序在第二阶段接入时，是直接请求 FastAPI，还是仍以 Web 会话为主、通过 Web 层桥接？
- 哪些原型服务测试需要保留为契约回归，哪些应该在 FastAPI 落地后重写为新的接口测试？
