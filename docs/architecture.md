# 基础架构方向

状态：Draft

## 当前生产级基础工程补充

当前仓库已经补齐一套可继续扩展的统一工程底座：

- Web：`apps/web` 继续保持现有原型交互，同时接入统一公开运行时配置
- Backend：`apps/backend` 作为正式主线，统一了版本化 API、响应壳、异常处理、request-id 和结构化日志
- Shared：`packages/protocol` 保存共享协议，`packages/config` 保存公开环境变量键和日志字段约定
- Infra：`infra/` 保存 Docker、Compose、Nginx、PostgreSQL / pgvector 初始化资产

当前推荐的运行拓扑变成：

```text
Browser
  |
  v
Nginx
  | \
  |  \__ static assets (apps/web dist)
  v
FastAPI (apps/backend)
  | \
  |  \__ Aliyun OSS boundary
  v
PostgreSQL + pgvector
```

这里的重点是先把“运行契约”统一，而不是提前实现具体业务。

## 统一 Document Service 边界

当前资料管理已经进一步收敛为统一 Document Service：

- Resume / JD / Knowledge 三类文档共享同一套上传、存储、元数据、删除和权限规则
- 二进制文件进入阿里云 OSS，对象键采用唯一命名，避免同名覆盖
- 文档元数据以 PostgreSQL 结构为目标事实源，包含归属用户、文档类型、对象键、大小、状态和删除标记
- 后续 Document Processing Pipeline 只从文档服务领取待处理文档或回写状态，不直接接管上传生命周期

这层边界刻意不包含：

- 文档解析
- Markdown 转换
- Chunk
- Embedding
- 向量数据库
- RAG

## 当前决策

当前 MVP 第一阶段已经确认以下工程方向：

- Web 原型实现继续沿用 `React + TypeScript + Vite`
- 正式服务端基础工程使用 `FastAPI`
- 桌面伴随程序仍属于后续独立客户端范围，不在本阶段实现
- 现有 `apps/api` TypeScript 服务保留为原型参考与契约样本；新的 FastAPI 基础工程落在 `apps/backend`

这样处理的原因是：当前前端原型已经验证了主要体验，适合直接作为 MVP 展示层基线；而服务端需要切换到更适合文件上传、AI 编排和 Python 生态集成的正式方向，同时又不能一次性重写掉已有原型参考。

## 目标边界

```text
apps/*
  可独立运行和交付的客户端或服务

packages/*
  被多个应用复用的 UI、类型、业务逻辑和配置

ai/*
  Prompt、评测集与脱敏输入样本

specs/*
  功能行为、实现设计、任务和验收依据
```

当前推荐的第一阶段目录职责如下：

```text
apps/web
  React 原型与 MVP Web 展示层；页面结构与交互保持已验证原型

apps/backend
  FastAPI 服务端基础工程；提供版本化 API、健康检查、占位路由与配置骨架

apps/api
  TypeScript 原型服务参考；保留既有契约、测试样本和原型行为，不作为正式后端主线继续扩展

packages/protocol
  共享协议、领域类型、前端可复用契约与原型兼容层

ai/
  Prompt、评测集、脱敏样本与未来 AI 编排资产
```

## MVP 第一阶段运行架构

```text
React Web client      Desktop companion (future)
        |                      |
        |                      v
        +--------------> FastAPI Application API
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
        User/session/material state   AI orchestration ports
                                               |
                                               v
                                 Model / speech / retrieval providers
```

这里表达的是 MVP 第一阶段的职责边界，而不是最终部署或供应商绑定。FastAPI 当前只需要提供可运行骨架与占位接口；上传简历、JD、RAG、实时回答、截图回答等真实业务逻辑将通过后续变更逐步接入。

## 关键设计约束

- 密钥和模型调用应由可信服务端管理。
- 音频采集、转录、生成和存储应保持可独立替换。
- 实时链路与非实时复盘应分开设计和测量。
- 数据保存期限与删除能力必须进入数据模型设计。
- AI 输出应可追踪到 Prompt 版本与评测基线。
- 前端页面结构与交互在工程底座阶段不得被工程改造顺手重做。
- 第一阶段占位接口必须显式返回“未实现”或空实现结构，不伪造真实业务结果。

## 第一阶段工程基线

为支持 MVP 继续开发，当前工程基线采用：

1. Web 端通过统一通信层读取 Backend API；产品运行时不再提供 fixture/prototype 数据源切换。
2. FastAPI 提供 `/healthz`、`/api/v1` 根路径、`/api/v1/web/state` 聚合状态接口和按功能域拆分的路由。
3. 简历、JD、知识库 / RAG、实时回答、截图回答、会话管理都保留独立模块边界，并通过聚合状态接口支撑当前 Web 体验。
4. 与供应商相关的文件存储、解析、检索、生成和流式输出能力保持可替换扩展点；本地测试不得用产品 runtime fixture 掩盖缺失接口。

## 积分兑换码原型边界

当前兑换码实现用于验证产品流程和安全契约：协议类型位于 `packages/protocol`，服务端原型位于 `apps/api`，积分页交互位于 `apps/web`。原型已经实现服务端定额、HMAC 摘要、一次性加密导出、账号与风险来源限流、原子入账模拟、不可变流水及审计；浏览器只提交兑换码和幂等键。

进入生产部署前必须替换以下内存适配器，不能把当前单进程实现直接视为多实例生产保证：

- 使用带唯一约束和行锁/条件更新的生产数据库事务，覆盖兑换码、批次、兑换记录和钱包流水。
- 使用 KMS 或同等服务托管版本化 HMAC pepper 与一次性导出密钥，密钥不得进入数据库、前端配置或普通日志。
- 使用跨实例共享的分布式限流与风险信号存储，并配置数据保留和轮换策略。
- 将一次性导出接入受权限控制、短时有效、单次读取的对象存储或密钥封装服务。

这些适配器替换不改变 `points-redemption-codes` 的用户行为和协议结果；若要支持共享活动码、会员兑换或自动发码，需要另建 OpenSpec 变更。
