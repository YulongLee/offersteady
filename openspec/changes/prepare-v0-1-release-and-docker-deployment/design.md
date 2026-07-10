## Context

OfferSteady 当前处于原型到 v0.1 早期商业化验证的交界点：Web、Backend、资料/RAG、短信登录、截图回答、积分和码支付都已经有本地实现或集成雏形。用户计划先把本地代码上传到 GitHub，再在 Ubuntu 24.04 服务器上拉取代码并通过 Docker/Compose 创建服务。

仓库已经存在 `infra/docker/backend.Dockerfile`、`infra/docker/web.Dockerfile`、`infra/compose/docker-compose.foundation.yml` 和 `infra/nginx/default.conf`，因此本变更不重新选择部署技术栈，而是在现有基线上补齐 v0.1 封板、环境变量、公网支付回调、健康检查和发布验收。

v0.1 的核心约束是“能真实访问、能小规模验证、不能泄露密钥”。这不是最终生产架构：当前部分仓储仍可能是内存实现，桌面助手权限和实时音频链路仍在持续打磨，完整 CI/CD、审计后台、灰度发布和高可用不是本轮目标。

## Goals / Non-Goals

**Goals:**

- 将 v0.1 封板流程标准化：本地验证、GitHub 安全上传、服务器拉取、Docker 构建/启动、健康检查和人工验收。
- 复用现有 Docker、Compose 和 Nginx 基线，补齐真实服务器部署所需的环境变量、端口、CORS、Web API 地址和支付回调地址。
- 确保码支付自动到账链路具备公网 `notify_url` 与 `return_url`，不再使用本地 `127.0.0.1` 作为真实回调。
- 明确 v0.1 发布前必须通过的最小验证命令和冒烟路径。
- 明确哪些风险允许进入 v0.1，但必须在发布说明中标注并作为 v0.2/商业化硬化任务跟进。

**Non-Goals:**

- 不在本变更内完成完整 CI/CD、蓝绿部署、Kubernetes、自动扩缩容或多机高可用。
- 不在本变更内重构所有内存仓储为 PostgreSQL 持久化，除非发布验收发现必须阻断 v0.1。
- 不在本变更内完成正式域名、HTTPS 证书、ICP备案或长期证书自动续期；若用户提供域名和证书条件，可作为部署配置输入。
- 不在本变更内改变已确认的产品原型页面结构和核心交互。
- 不把任何 OSS、短信、模型、数据库、支付密钥提交到 GitHub。

## Decisions

### 1. 以 GitHub + 服务器拉取代码作为 v0.1 交付路径

采用用户计划的流程：本地封板后上传 GitHub，服务器通过 Git 拉取代码，再运行 Docker/Compose。这样便于在当前阶段快速复现和人工排障。

备选方案是直接从本地打包上传服务器。它更快，但不利于版本追踪、回滚和后续协作，因此不作为主路径。

### 2. 复用现有 Compose 基线，先做单机部署

v0.1 使用单台 Ubuntu 24.04 服务器运行 Web、Backend、PostgreSQL/pgvector 和 Nginx 入口。Compose 已经具备 postgres、backend、web 三个服务，后续实现阶段只需补齐生产变量、网络、健康检查和持久卷。

备选方案是拆成云数据库、对象存储、独立反向代理和容器编排平台。它更接近正式商业化，但对 v0.1 小规模验证过重。

### 3. 服务端密钥只通过服务器环境注入

`.env` 和 `.env.local` 只能用于本地；GitHub 只提交 `.env.example` 和文档。服务器使用 `.env.production` 或部署平台 secret 文件，并确保该文件被 `.gitignore` 排除。

备选方案是在 Compose 文件中写默认密钥。它会降低部署门槛，但会制造严重泄露风险，不采用。

### 4. 码支付回调必须切换为公网地址

v0.1 真实支付验收必须设置：

```text
OFFERSTEADY_MZFPAY_NOTIFY_URL=https://<server-host>/api/v1/billing/payment-providers/mzfpay/notify
OFFERSTEADY_MZFPAY_RETURN_URL=https://<server-host>/app/billing
OFFERSTEADY_PUBLIC_WEB_BASE_URL=https://<server-host>
```

如果暂时没有域名或 HTTPS，允许短期使用公网 IP + HTTP 做内部测试，但必须在发布说明中标注支付平台回调、浏览器安全和用户信任风险。

### 5. Web API 地址由部署目标决定

前端 Docker 构建时的 `VITE_API_BASE_URL` 必须指向部署后的后端入口。若 Nginx 同域代理 `/api/`，则推荐使用同源根地址；若前后端分离端口暴露，则必须同步配置 CORS。

备选方案是在前端运行时读取可变配置文件。它更灵活，但当前 Web Dockerfile 是构建期注入模型，本轮优先保持简单。

### 6. v0.1 允许标注性风险，不允许静默风险

若某些能力仍是 MVP 级实现，例如账务订单未完全持久化、实时语音链路不稳定、桌面助手权限需要手动处理，可以进入 v0.1 内测，但必须在发布清单中标注状态、影响和规避方式。用户可见的付费、资料和账号能力不得静默丢失数据。

## Risks / Trade-offs

- [服务器公网 IP 暴露 HTTP 服务] → 优先使用 Nginx 单入口并限制只暴露 80/443；若无 HTTPS，限定内测范围并尽快补证书。
- [支付平台无法访问本地回调] → 部署前必须把 `notify_url` 改成服务器公网地址，并用测试订单验证后端收到回调。
- [密钥误提交 GitHub] → 封板前检查 `.gitignore`、`git status` 和 secret scanning；只提交 `.env.example`。
- [Web 构建期 API 地址错误] → Docker 构建和部署文档必须明确 `VITE_API_BASE_URL`，发布验收访问浏览器真实页面并创建一笔测试订单。
- [内存仓储导致重启丢状态] → v0.1 发布说明中标注受影响能力；付费订单和用户权益若未持久化则不得面向真实付费用户开放。
- [单机资源不足] → v0.1 限制小规模测试，保留日志和健康检查；模型调用走外部服务，不在服务器本机跑大模型。
- [外部供应商配置不完整] → 部署验收需要逐项检查 OSS、短信、MinerU、Chat、Vision、Embedding、Rerank、ASR 和支付配置是否存在，并区分“阻断发布”和“可延后能力”。

## Migration Plan

1. 本地完成 v0.1 封板前检查：前端 typecheck/build、关键测试、后端健康检查、OpenSpec validate、支付订单创建 smoke。
2. 清理仓库敏感信息：确认 `.env`、`.env.local`、日志、真实简历、真实截图和密钥文件不进入 Git。
3. 上传 GitHub：创建远端仓库、推送当前封板分支或 `v0.1.0` tag。
4. 服务器准备：安装 Docker、Docker Compose plugin、Git，开放必要端口，拉取仓库。
5. 服务器配置：创建 `.env.production`，写入数据库、OSS、短信、模型、MinerU、RAG、ASR、码支付、CORS 和 Web API 地址。
6. 启动服务：使用 Compose 构建并启动 postgres、backend、web/Nginx。
7. 验收服务：访问 Web 页面、Backend `/healthz`、`/api/v1/billing/status`，创建码支付订单，确认收银台链接可打开。
8. 支付回调验收：使用小额或测试订单确认码支付平台能访问服务器 `notify_url`，后端验签后订单状态变更。
9. 封板记录：记录 commit/tag、服务器 IP、开放端口、环境变量版本、已知风险和回滚命令。
10. 回滚：若发布失败，停止 Compose 服务，回退到上一 tag 或本地启动方式，保留日志用于排障。

## Open Questions

- v0.1 是否使用正式域名和 HTTPS，还是先用公网 IP 内测？
- 码支付平台是否允许 HTTP 公网 IP 回调，还是要求 HTTPS 域名？
- v0.1 是否允许真实用户付费，还是只允许管理员和少量测试账号验证？
- 哪些当前内存态能力必须在 v0.1 前改为 PostgreSQL 持久化，哪些可以标注为已知风险？
- GitHub 仓库是私有仓库还是公开仓库？如果公开，是否需要额外做 secret/history 扫描？
