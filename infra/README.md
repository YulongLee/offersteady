# OfferSteady Infrastructure Baseline

`infra/` 保存生产级基础工程相关的共享部署资产，而不是业务逻辑。

目录约定：

- `docker/`: Web、Backend 的镜像构建文件
- `compose/`: 本地与生产相近环境的多服务启动基线
- `nginx/`: 统一入口、静态资源分发与 API 反向代理配置
- `caddy/`: 公网 TLS 入口配置；生产实时字幕 SSE 路由禁止响应压缩并强制即时 flush
- `postgres/`: PostgreSQL / pgvector 初始化脚本与约定

敏感配置通过环境变量注入，不写入仓库。

## v0.1 单机部署

v0.1 推荐使用一台 Ubuntu 24.04 服务器，通过 GitHub 拉取代码并运行：

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --build
```

`.env.production` 必须只存在于服务器，不提交 Git。完整步骤见 [`docs/v0-1-server-deployment.md`](../docs/v0-1-server-deployment.md)。

生产宿主机 Caddy 使用 `caddy/Caddyfile.production`。部署前必须运行
`caddy validate --config infra/caddy/Caddyfile.production`，更新时保留旧配置副本，
并确认实时字幕 SSE 响应没有 `Content-Encoding`。普通页面和接口继续使用 gzip。

## 支付回调

官方微信支付与支付宝的新订单渠道通过运营后台独立配置。部署后两种渠道默认关闭；商户材料录入和小额验收流程见 [`../docs/payment-channel-operations.md`](../docs/payment-channel-operations.md)。

真实码支付自动到账必须配置公网可访问的：

```text
OFFERSTEADY_MZFPAY_NOTIFY_URL=http(s)://<host>/api/v1/billing/payment-providers/mzfpay/notify
OFFERSTEADY_MZFPAY_RETURN_URL=http(s)://<host>/app/billing
```

本地 `127.0.0.1` 地址只能用于开发，不能用于平台回调。

切换支付宝开放平台官方支付时配置：

```text
OFFERSTEADY_CHECKOUT_PROVIDER=alipay
OFFERSTEADY_ALIPAY_NOTIFY_URL=https://<host>/api/v1/billing/payment-providers/alipay/notify
OFFERSTEADY_ALIPAY_RETURN_URL=https://<host>/app/billing
```

支付宝应用私钥、支付宝公钥、APPID 和卖家 PID 通过服务器密钥环境注入。切换只影响新订单，历史 MZFPay 订单不会迁移或重算。
