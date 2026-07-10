# OfferSteady Infrastructure Baseline

`infra/` 保存生产级基础工程相关的共享部署资产，而不是业务逻辑。

目录约定：

- `docker/`: Web、Backend 的镜像构建文件
- `compose/`: 本地与生产相近环境的多服务启动基线
- `nginx/`: 统一入口、静态资源分发与 API 反向代理配置
- `postgres/`: PostgreSQL / pgvector 初始化脚本与约定

敏感配置通过环境变量注入，不写入仓库。

## v0.1 单机部署

v0.1 推荐使用一台 Ubuntu 24.04 服务器，通过 GitHub 拉取代码并运行：

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --build
```

`.env.production` 必须只存在于服务器，不提交 Git。完整步骤见 [`docs/v0-1-server-deployment.md`](../docs/v0-1-server-deployment.md)。

## 支付回调

真实码支付自动到账必须配置公网可访问的：

```text
OFFERSTEADY_MZFPAY_NOTIFY_URL=http(s)://<host>/api/v1/billing/payment-providers/mzfpay/notify
OFFERSTEADY_MZFPAY_RETURN_URL=http(s)://<host>/app/billing
```

本地 `127.0.0.1` 地址只能用于开发，不能用于平台回调。
