## Why

OfferSteady 已经完成一轮原型功能开发，并开始接入短信登录、资料/RAG、面试问答、截图回答、积分和码支付等真实能力。现在需要先形成 v0.1 封板与部署规范，确保代码上传 GitHub、服务器拉取代码、Docker 服务创建和公网支付回调具备一致的验收边界。

## What Changes

- 新增 v0.1 发布封板能力，定义本地代码进入 GitHub、服务器拉取、Docker Compose 启动、Nginx 入口、环境变量和健康检查的最小闭环。
- 明确 v0.1 是“早期商业化验证版本”，允许部分能力仍为 MVP/内存实现，但必须标注风险、禁止泄露密钥，并保证用户可访问 Web 与 Backend。
- 将码支付回调公网化纳入发布前检查：`notify_url` 和 `return_url` 必须指向服务器公网地址，而不是本地 `127.0.0.1`。
- 建立封板前验证清单：前端 typecheck/build、关键页面冒烟、后端健康检查、Docker 构建、API 可访问、支付订单创建、OSS/数据库/模型配置存在性检查。
- 定义发布后不在 v0.1 范围内的硬化项：完整 CI/CD、蓝绿部署、自动扩缩容、正式证书自动续期、全量数据库迁移体系、全功能压测和审计后台。
- 补充 GitHub 上传前的安全要求：`.env`、密钥、OSS/短信/模型/支付密钥不得进入仓库；只提交 `.env.example` 和部署变量说明。

## Capabilities

### New Capabilities

- `v0-1-release-deployment-readiness`: 定义 v0.1 封板、GitHub 代码交付、服务器 Docker 部署、环境变量、健康检查、支付公网回调和发布验收规则。

### Modified Capabilities

无。当前变更只新增发布与部署就绪能力，不改变既有面试、资料、RAG、短信登录、积分和支付业务行为。

## Impact

- 影响 `infra/`：Docker Compose、Web/Backend Dockerfile、Nginx 配置、部署环境变量约定可能需要补齐或修正。
- 影响 `docs/`：需要补充 v0.1 发布说明、服务器部署步骤、环境变量清单和回滚/重启说明。
- 影响根目录配置：需要确保 `.gitignore`、`.env.example`、README 本地/部署说明不误导用户提交密钥。
- 影响后端配置：`OFFERSTEADY_PUBLIC_WEB_BASE_URL`、`OFFERSTEADY_MZFPAY_NOTIFY_URL`、`OFFERSTEADY_MZFPAY_RETURN_URL`、CORS、OSS、短信、模型和数据库配置需要可由服务器环境注入。
- 影响前端配置：`VITE_API_BASE_URL` 需要在 Docker 构建或运行方案中明确指向后端公网入口。
- 影响运维流程：v0.1 需要可在用户提供的 Ubuntu 24.04 服务器上通过 GitHub 拉代码并以 Docker/Compose 启动。
