## Context

OfferSteady 现在已经从纯原型阶段往 MVP 工程阶段走了一步：前端保留了 `React + TypeScript + Vite` 的可运行原型，后端已经有 `FastAPI` 基础骨架，也开始接入上传、协议和部分真实接口边界。但这些工作更多是“让开发能开始”，还不是一套真正面向后续所有业务模块的生产级统一底座。

你这次提出的目标很明确：不是做某一个业务功能，而是把整个项目后续会持续依赖的基础工程一次性规划好，并且范围已经明确包含：

- React + TypeScript 工程
- FastAPI 工程
- PostgreSQL
- pgvector
- 阿里云 OSS
- Docker
- Nginx
- 环境变量管理
- 配置管理
- 日志管理
- 模块目录规范
- API 规范
- 统一异常处理
- 统一响应结构

同时你也明确了边界：不实现具体业务逻辑。

这意味着这次变更的核心不是“上线某个功能”，而是把当前零散的骨架、约定和未来依赖统一成一套生产级平台基线，让后面的账号、资料上传、RAG、实时回答、计费、桌面桥接都能在同一套规则下扩展。

## Goals / Non-Goals

**Goals:**

- 定义 OfferSteady 的生产级统一基础工程结构，覆盖前端、后端、数据库、向量检索扩展、对象存储与部署基线
- 为前端和后端建立统一的配置、日志、错误处理、响应结构和目录规范
- 为 PostgreSQL、pgvector 和 OSS 明确稳定的接入边界，而不是让后续功能各自直接耦合基础设施
- 为容器化、本地联调、测试环境和生产相近环境提供一致的启动与部署约定
- 为后续所有业务模块提供统一扩展落位点，而不是再次从零决定工程规范

**Non-Goals:**

- 不实现任何具体业务逻辑，例如简历解析、向量索引、实时回答、支付回调或账号鉴权
- 不在本次变更中最终锁定所有生产供应商以外的可替换 AI 组件
- 不把当前产品原型页面结构和交互重做成新的产品流程
- 不在本次变更中完成云上正式部署，只建立生产级基础工程和部署基线

## Decisions

### 1. Build on the current React + FastAPI direction instead of reopening the application stack choice

当前仓库已经明确把 Web 展示层放在 `apps/web`，把正式服务端主线放在 `apps/backend`。这次生产级基础工程继续沿用这条方向，而不是重新讨论是否换成 Next.js、NestJS 或别的栈。

原因是：

- 前端原型已经大量沉淀在 React 组件与交互里
- FastAPI 更适合后续文件上传、AI 编排、异步任务与 Python 生态
- 现在真正缺的不是“换栈”，而是“把既定栈做成统一平台”

替代方案是趁机重新评估整个应用框架，但那会把“生产级工程化”与“技术路线推翻重选”绑在一起，成本很高，也会拖慢后续业务推进。

### 2. Standardize around a layered monorepo with clear ownership boundaries

推荐把仓库长期维持为单仓多应用结构，但把职责进一步收紧：

- `apps/web`: React + TypeScript 产品前端
- `apps/backend`: FastAPI 应用 API
- `packages/protocol`: 前后端共享协议与契约类型
- `packages/config`: 共享配置常量、环境变量键、日志字段约定
- `packages/ui` 或等效目录：如果后续前端组件复用增多，再抽取共享 UI
- `infra/` 或等效目录：Docker、Nginx、Compose、部署模板、数据库初始化脚本
- `ai/`: Prompt、eval、脱敏样本

这样做的原因是：你后面会同时演进前端、后端、桌面端、协议、部署和 AI 资产，如果没有稳定边界，所有基础逻辑会继续堆在应用目录里。

替代方案是让部署资产继续散落在根目录或每个应用各自维护一套配置。短期省事，但长期会让本地运行、CI 和生产环境不断分叉。

### 3. Use PostgreSQL as the transactional source of truth and pgvector as an extension capability, not a second database system

在生产级底座里，`PostgreSQL` 作为核心事务数据源，承载账号、会话、资料元数据、计费、任务记录和审计数据；`pgvector` 作为 PostgreSQL 内的向量检索扩展能力，而不是额外再并列引入第二套向量数据库。

这样做的原因是：

- MVP 阶段运维复杂度更低
- 资料元数据与检索索引更容易保持一致性
- 对后续 RAG 来说，先让主数据和向量能力同源，比“一开始就拆双库”更稳

替代方案是直接引入独立向量数据库。这样在极大规模时更灵活，但对当前阶段来说会增加部署、备份、观测和一致性成本。

### 4. Treat Aliyun OSS as the canonical object storage boundary

所有文档、截图、导出文件和可能的后续临时产物，都通过统一对象存储边界接入阿里云 OSS。应用层只依赖抽象存储接口，不直接在业务模块里散落 OSS SDK 调用。

推荐边界：

- 上传意图/签名能力
- 对象确认与元数据登记
- 受控读取地址或内部读取能力
- 逻辑删除与异步清理

这样做能避免后续简历、JD、知识材料、截图和导出各自形成不同的 OSS 用法。

替代方案是业务模块各自直接接入 OSS。这样会让权限、对象命名、清理策略和错误处理不断重复。

### 5. Separate runtime configuration from code and make it environment-first

生产级基础工程必须把配置当作一等公民处理。推荐采用：

- 开发、测试、预发、生产分层配置
- 环境变量作为最终注入入口
- 应用内部只暴露类型化配置对象
- 前端和后端分别维护“可公开配置”与“服务端私有配置”边界

重点不是“有没有 `.env`”，而是保证：

- 同一配置键在全项目有唯一语义
- 默认值只用于本地开发或安全兜底
- 敏感变量不进入前端构建产物、测试夹具或普通日志

替代方案是继续让每个应用分别自行定义环境变量和默认值。这会让团队后续很难知道哪些变量是正式约定、哪些只是临时实现。

### 6. Define one structured logging baseline across app, worker and ingress

日志管理推荐统一为结构化日志基线，并约定字段，例如：

- `timestamp`
- `level`
- `service`
- `environment`
- `request_id`
- `user_id`（可选、脱敏）
- `feature`
- `action`
- `error_code`

FastAPI、后台任务、数据库迁移脚本和 Nginx 接入层都应围绕这个基线工作。前端只保留必要调试与错误上报接口，不把浏览器控制台当作正式日志系统。

替代方案是先继续使用各组件默认日志格式。这样能跑，但后续排查跨服务问题会非常痛苦。

### 7. Make API response and exception handling a platform concern, not a per-module choice

后端的统一响应结构、错误码和异常处理必须在平台层先定下来。所有业务模块都复用这一套规范，而不是等业务功能做起来后再一点点回收。

推荐统一响应壳至少包含：

- `success`
- `data`
- `error`
- `requestId`
- `meta`

推荐错误结构至少包含：

- `code`
- `message`
- `details`

同时把异常分成：

- 验证错误
- 领域错误
- 权限错误
- 依赖错误
- 未实现错误
- 未知系统错误

替代方案是继续沿用混合返回：有的接口直接返回对象，有的接口返回占位壳，有的接口抛框架默认错误。这样短期灵活，长期会拖慢所有客户端和测试开发。

### 8. Use Docker + Nginx as the canonical deployment baseline

生产级底座需要一个明确的运行与交付标准：

- Docker 构建 Web 与 Backend
- PostgreSQL + pgvector 通过容器/服务接入
- Nginx 作为统一入口，负责静态资源与反向代理
- 本地开发与生产相近环境都能复用相同服务拓扑

这样做的原因是：后面不论你最终上云方式是 ECS、容器服务还是别的，先把交付单元和入口方式标准化，后面的部署才不会每个阶段都重来。

替代方案是先只用本地进程跑，等后面再补 Docker/Nginx。这样会让本地、测试和生产环境差异越来越大。

## Risks / Trade-offs

- [Risk] 生产级基础工程一次性纳入的内容较多，容易让变更看起来偏“大平台” → Mitigation: 明确只实现底座，不实现业务逻辑，并在 tasks 中按前端、后端、数据、部署分批切片
- [Risk] 过早工程化可能拖慢短期业务推进 → Mitigation: 只收敛那些后续每个模块都会重复依赖的底层能力，不提前引入不必要的平台复杂度
- [Risk] PostgreSQL + pgvector 先合并使用，未来超大规模时可能需要再演进 → Mitigation: 在设计上保留检索适配器边界，避免把业务直接写死到 SQL 细节
- [Risk] Docker/Nginx 基线如果和实际云上环境偏差过大，会形成“看似统一、实际分叉” → Mitigation: 在部署资产里强调入口职责和运行契约，而不是绑定过多云厂商特性
- [Risk] 统一响应结构会与现有部分原型接口形状不一致 → Mitigation: 把这次变更定位为平台规范变更，后续实现型 change 按同一标准逐步迁移

## Migration Plan

1. 先完成生产级基础工程的规范与目录方案，作为后续所有实现型 change 的共同前置基线。
2. 再在 apply 阶段分步落地：共享配置与环境变量、后端平台层、数据库与 pgvector 接入、Docker/Nginx、前端构建与运行约定。
3. 保留现有原型和 MVP 第一阶段的可运行性，但逐步把新的平台规范接到正式主线中。
4. 后续上传、RAG、实时回答、支付、桌面桥接等 change 都直接建立在这次统一底座之上，而不是重复各自定义基础设施。

回滚策略：

- 如果某个基础设施接入方式需要调整，优先回滚对应平台实现，不回滚产品原型页面与业务规范
- 对于统一响应结构和异常处理，允许在过渡期做兼容层，但不回退到“各模块随意返回”

## Open Questions

- 数据库迁移工具最终选择什么：Alembic 还是其他方式？
- 是否在这一阶段同时为后台异步任务预留独立 worker 进程骨架？
- Nginx 之外是否还需要提前考虑 CDN / 对象存储静态资源策略，还是留到后续部署变更？
- 前端共享配置与后端共享配置是否抽成同一个 `packages/config`，还是分别在应用层保留类型化封装？
