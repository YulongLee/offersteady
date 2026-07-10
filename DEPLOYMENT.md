# OfferSteady v0.1 Deployment Quick Start

This document is the short operator-facing deployment flow for v0.1. For full details, see [`docs/v0-1-server-deployment.md`](docs/v0-1-server-deployment.md).

## Target

- Server: Ubuntu 24.04
- Deployment mode: single-server Docker Compose
- Repository: `git@github.com:YulongLee/offersteady.git`
- Current public IP for internal testing: `101.133.147.212`

## First-time server setup

Install Docker, Docker Compose plugin, and Git:

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

Log out and back in, then verify:

```bash
docker --version
docker compose version
git --version
```

## Pull code

```bash
sudo mkdir -p /opt/offersteady
sudo chown "$USER":"$USER" /opt/offersteady
cd /opt/offersteady
git clone git@github.com:YulongLee/offersteady.git app
cd app
```

If the server does not have GitHub SSH access yet, add a deploy key or use a temporary HTTPS clone method.

## Create production environment file

```bash
cp .env.example .env.production
chmod 600 .env.production
vim .env.production
```

At minimum, set the server host and callback URLs:

```bash
OFFERSTEADY_ENV=production
OFFERSTEADY_PUBLIC_WEB_BASE_URL=http://101.133.147.212
OFFERSTEADY_CORS_ALLOWED_ORIGINS=["http://101.133.147.212"]

VITE_APP_ENV=production
VITE_API_BASE_URL=http://101.133.147.212
VITE_PUBLIC_APP_VERSION=0.1.0

OFFERSTEADY_MZFPAY_NOTIFY_URL=http://101.133.147.212/api/v1/billing/payment-providers/mzfpay/notify
OFFERSTEADY_MZFPAY_RETURN_URL=http://101.133.147.212/app/billing
```

Also fill real server-side secrets, including database password, JWT secret, OSS, SMS, model providers, MinerU, RAG providers, ASR provider, and MZFPay credentials.

Never commit `.env.production`.

## One-command deploy after setup

From the repository root on the server:

```bash
bash scripts/deploy-v0.1.sh
```

The script will:

- verify Docker and Compose are available
- verify `.env.production` exists
- pull latest code when the working tree is clean
- build and start Docker Compose services
- run health checks
- print frontend and backend URLs

## Manual deploy command

If you do not want to use the script:

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --build
```

## Smoke checks

```bash
curl -fsS http://101.133.147.212/healthz
curl -fsS http://101.133.147.212/api/v1/billing/status
```

Open the Web app:

```text
http://101.133.147.212/
```

## Payment callback requirement

MZFPay automatic settlement only works when the provider can reach:

```text
http://101.133.147.212/api/v1/billing/payment-providers/mzfpay/notify
```

Do not claim automatic settlement is ready while `notify_url` points to `127.0.0.1`, `localhost`, or a private network address.

## Operations

View logs:

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml logs -f backend
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml logs -f web
```

Restart:

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml restart
```

Stop:

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml down
```

Rollback:

```bash
git fetch --tags
git checkout <previous-good-tag-or-commit>
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --build
```
