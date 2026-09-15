# Standalone Baidu ranking tool

This tool runs locally and is deliberately isolated from the OfferSteady production API, admin console, database, and website. It queries the configured Baidu PC ranking provider and writes optional JSON/Markdown reports for SEO analysis.

## Configure locally

Use an untracked shell environment or local env file. Choose one authentication mode:

```bash
export BAIDU_RANKING_ENDPOINT='https://seozbbdpcpm.api.bdymkt.com/seo/baidu/pc/ranking'
export BAIDU_RANKING_DOMAIN='mianshiwen.cn'
export BAIDU_RANKING_APP_CODE='your-app-code'
```

Or use the provider's AccessKey/Secret pair:

```bash
export BAIDU_RANKING_ACCESS_KEY='your-access-key'
export BAIDU_RANKING_SECRET_KEY='your-secret-key'
```

Never commit the local env file, put these values in a browser bundle, or paste them into a report. Credentials shown in screenshots should be rotated before long-term use.

## Run

From the repository root:

```bash
PYTHONPATH=. python3 -m tools.baidu_ranking --keyword 'AI面试助手' --format both
PYTHONPATH=. python3 -m tools.baidu_ranking --batch --format both
```

Batch mode uses the configured keyword list, is capped by `BAIDU_RANKING_MAX_KEYWORDS` (default 50), and waits between requests. The report keeps provider rank labels such as `3-2` unchanged; it does not invent an absolute rank.

Useful local settings include `BAIDU_RANKING_TIMEOUT_SECONDS`, `BAIDU_RANKING_RETRY_ATTEMPTS`, `BAIDU_RANKING_DELAY_SECONDS`, and `BAIDU_RANKING_OUTPUT_DIR`.
