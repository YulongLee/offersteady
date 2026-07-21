# v0.1 Server Deployment Runbook

目标服务器：Ubuntu 24.04，单机 Docker Compose 部署。

## 1. Server Prerequisites

在服务器上安装 Docker、Compose plugin 和 Git：

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc >/dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

重新登录 SSH 后确认：

```bash
docker --version
docker compose version
git --version
```

安全组/防火墙至少开放：

- `22/tcp`：SSH，仅限管理员 IP 更安全。
- `80/tcp`：HTTP 内测入口。
- `443/tcp`：HTTPS，配置证书后使用。

## 2. Pull Code

```bash
sudo mkdir -p /opt/offersteady
sudo chown "$USER":"$USER" /opt/offersteady
cd /opt/offersteady
git clone <GITHUB_REPO_URL> app
cd app
git checkout <V0_1_BRANCH_OR_TAG>
```

`<GITHUB_REPO_URL>` 和 `<V0_1_BRANCH_OR_TAG>` 由封板记录填写。

## 3. Server Environment File

在仓库根目录创建服务器专用环境文件，不提交 Git：

```bash
cp .env.example .env.production
chmod 600 .env.production
```

必须替换以下变量：

```bash
OFFERSTEADY_ENV=production
OFFERSTEADY_PUBLIC_WEB_BASE_URL=http://101.133.147.212
OFFERSTEADY_CORS_ALLOWED_ORIGINS=["http://101.133.147.212"]
VITE_APP_ENV=production
VITE_API_BASE_URL=http://101.133.147.212
VITE_PUBLIC_APP_VERSION=0.1.0

POSTGRES_DB=offersteady
POSTGRES_USER=offersteady
POSTGRES_PASSWORD=<replace-with-strong-password>
OFFERSTEADY_DATABASE_URL=postgresql://offersteady:<replace-with-strong-password>@postgres:5432/offersteady

OFFERSTEADY_AUTH_JWT_SECRET=<replace-with-long-random-secret>
OFFERSTEADY_MATERIAL_USER_HASH_SALT=<replace-with-long-random-salt>

OFFERSTEADY_MZFPAY_BASE_URL=https://pay.mzfpay.com
OFFERSTEADY_MZFPAY_PID=<merchant-id>
OFFERSTEADY_MZFPAY_KEY=<merchant-key>
OFFERSTEADY_MZFPAY_SUBMIT_PATH=/xpay/epay/submit.php
OFFERSTEADY_MZFPAY_NOTIFY_URL=https://mianshiwen.cn/api/v1/billing/payment-providers/mzfpay/notify
OFFERSTEADY_MZFPAY_RETURN_URL=https://mianshiwen.cn/app/billing
OFFERSTEADY_MZFPAY_PAYMENT_TTL_SECONDS=900
```

如果已有域名和 HTTPS，把所有 `http://101.133.147.212` 替换为 `https://<domain>`。

后端密钥只放 `.env.production` 或服务器密钥管理系统，不放前端源码和 GitHub。

## 4. Start Services

```bash
cd /opt/offersteady/app
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --build
```

查看状态：

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml ps
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml logs -f backend
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml logs -f web
```

## 5. Smoke Tests

服务器本机：

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/api/v1/billing/status
curl -I http://127.0.0.1:8080/
```

外部浏览器：

```text
http://101.133.147.212/
http://101.133.147.212/api/v1/billing/status
```

在 Web 积分页点击商品购买，应打开 `https://pay.mzfpay.com/...` 收银台链接，且链接对应商品价格。

## 6. Payment Callback Check

码支付自动到账只有在平台能访问 `OFFERSTEADY_MZFPAY_NOTIFY_URL` 时才成立。

检查要求：

- `notify_url` 不包含 `127.0.0.1` 或 `localhost`。
- 服务器安全组允许外部访问 HTTP/HTTPS 入口。
- 后端日志能看到 `/api/v1/billing/payment-providers/mzfpay/notify` 请求。
- 重复通知不会重复加积分或重复开会员。

如果平台不支持 HTTP 公网 IP 回调，必须配置域名和 HTTPS 后再声明自动到账已就绪。

## 7. Operations

重启服务：

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml restart
```

更新环境变量后重启：

```bash
vim .env.production
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --build
```

停止服务：

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml down
```

不要删除数据库卷，除非明确要清空数据：

```bash
# 危险：会删除 PostgreSQL 数据
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml down -v
```

## 8. Rollback

```bash
cd /opt/offersteady/app
git fetch --tags
git checkout <PREVIOUS_GOOD_TAG_OR_COMMIT>
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --build
```

回滚后重新执行 Smoke Tests。
