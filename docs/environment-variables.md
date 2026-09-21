# 环境变量与密钥边界

## 服务端私有变量

- `OFFERSTEADY_DATABASE_URL`
- `OFFERSTEADY_OSS_ACCESS_KEY_ID`
- `OFFERSTEADY_OSS_ACCESS_KEY_SECRET`
- `OFFERSTEADY_MATERIAL_USER_HASH_SALT`
- `OFFERSTEADY_CHAT_QWEN_API_KEY`
- `OFFERSTEADY_SCREENSHOT_VISION_API_KEY`
- `OFFERSTEADY_EMBEDDING_API_KEY`
- `OFFERSTEADY_RERANK_API_KEY`
- `OFFERSTEADY_REALTIME_ASR_API_KEY`
- `OFFERSTEADY_INTEGRATION_MINERU_API_KEY`
- `OFFERSTEADY_ACCESS_TOKEN_SECRET`
- `OFFERSTEADY_AUTH_WECHAT_APP_SECRET`
- `OFFERSTEADY_AUTH_SMS_ALIYUN_ACCESS_KEY_ID`
- `OFFERSTEADY_AUTH_SMS_ALIYUN_ACCESS_KEY_SECRET`
- `OFFERSTEADY_AUTH_JWT_SECRET`
- `OFFERSTEADY_ADMIN_SESSION_SIGNING_SECRET`
- `OFFERSTEADY_ADMIN_ENCRYPTION_KEY`
- `OFFERSTEADY_PROMOTION_VISITOR_HMAC_SECRET`
- `OFFERSTEADY_MZFPAY_KEY`
- `OFFERSTEADY_MZFPAY_PID`
- `OFFERSTEADY_ALIPAY_APP_PRIVATE_KEY`
- `OFFERSTEADY_ALIPAY_PUBLIC_KEY`

这些变量只能进入后端运行环境、CI 密钥或部署平台密钥管理系统，不能出现在浏览器、前端源码常量或测试快照里。

## 服务端公共运行变量

- `OFFERSTEADY_APP_NAME`
- `OFFERSTEADY_APP_VERSION`
- `OFFERSTEADY_ENV`
- `OFFERSTEADY_API_PREFIX`
- `OFFERSTEADY_PUBLIC_WEB_BASE_URL`
- `OFFERSTEADY_CORS_ALLOWED_ORIGINS`
- `OFFERSTEADY_LOG_LEVEL`
- `OFFERSTEADY_PGVECTOR_SCHEMA`
- `OFFERSTEADY_PGVECTOR_EXTENSION_NAME`
- `OFFERSTEADY_OSS_BUCKET`
- `OFFERSTEADY_OSS_ENDPOINT`
- `OFFERSTEADY_OSS_REGION`
- `OFFERSTEADY_OSS_KEY_PREFIX`
- `OFFERSTEADY_OSS_ENVIRONMENT_LABEL`
- `OFFERSTEADY_OSS_UPLOAD_INTENT_TTL_SECONDS`
- `OFFERSTEADY_MATERIAL_MAX_FILE_SIZE_BYTES`
- `OFFERSTEADY_MATERIAL_MAX_PAGE_COUNT`
- `OFFERSTEADY_MATERIAL_MAX_TEXT_CHARACTERS`
- `OFFERSTEADY_MATERIAL_SUPPORTED_EXTENSIONS`
- `OFFERSTEADY_MATERIAL_PROCESSING_TIMEOUT_SECONDS`
- `OFFERSTEADY_MATERIAL_INDEXING_TIMEOUT_SECONDS`
- `OFFERSTEADY_MATERIAL_DELETION_GRACE_SECONDS`
- `OFFERSTEADY_MATERIAL_OBJECT_ID_BYTES`
- `OFFERSTEADY_DOCUMENT_PROCESSING_INLINE_WORKER_ENABLED`
- `OFFERSTEADY_DOCUMENT_PROCESSING_JOB_LEASE_SECONDS`
- `OFFERSTEADY_ACCESS_TOKEN_EXPIRE_MINUTES`
- `OFFERSTEADY_AUTH_REFRESH_TOKEN_TTL_SECONDS`
- `OFFERSTEADY_AUTH_WECHAT_PROVIDER_MODE`
- `OFFERSTEADY_AUTH_WECHAT_APP_ID`
- `OFFERSTEADY_AUTH_WECHAT_CALLBACK_URL`
- `OFFERSTEADY_AUTH_WECHAT_AUTHORIZATION_TTL_SECONDS`
- `OFFERSTEADY_AUTH_SMS_PROVIDER_MODE`
- `OFFERSTEADY_AUTH_SMS_ALIYUN_ENDPOINT`
- `OFFERSTEADY_AUTH_SMS_ALIYUN_REGION_ID`
- `OFFERSTEADY_AUTH_SMS_ALIYUN_SIGN_NAME`
- `OFFERSTEADY_AUTH_SMS_ALIYUN_TEMPLATE_CODE`
- `OFFERSTEADY_AUTH_SMS_CODE_PEPPER`
- `OFFERSTEADY_AUTH_SMS_TTL_SECONDS`
- `OFFERSTEADY_AUTH_SMS_SEND_INTERVAL_SECONDS`
- `OFFERSTEADY_AUTH_SMS_DAILY_LIMIT`
- `OFFERSTEADY_AUTH_SMS_VERIFY_ATTEMPT_LIMIT`
- `OFFERSTEADY_AUTH_SMS_FAKE_CODE`
- `OFFERSTEADY_AUTH_SMS_TEST_PHONE_NUMBER`
- `OFFERSTEADY_AUTH_EMAIL_ENABLED`
- `OFFERSTEADY_AUTH_EMAIL_PROVIDER_MODE`
- `OFFERSTEADY_AUTH_EMAIL_CODE_PEPPER`
- `OFFERSTEADY_AUTH_EMAIL_TTL_SECONDS`
- `OFFERSTEADY_AUTH_EMAIL_SEND_INTERVAL_SECONDS`
- `OFFERSTEADY_AUTH_EMAIL_DAILY_LIMIT`
- `OFFERSTEADY_AUTH_EMAIL_VERIFY_ATTEMPT_LIMIT`
- `OFFERSTEADY_AUTH_EMAIL_SMTP_HOST`
- `OFFERSTEADY_AUTH_EMAIL_SMTP_PORT`
- `OFFERSTEADY_AUTH_EMAIL_SMTP_USERNAME`
- `OFFERSTEADY_AUTH_EMAIL_SMTP_PASSWORD`
- `OFFERSTEADY_AUTH_EMAIL_SMTP_SSL`
- `OFFERSTEADY_AUTH_EMAIL_SMTP_STARTTLS`
- `OFFERSTEADY_AUTH_EMAIL_FROM_ADDRESS`
- `OFFERSTEADY_AUTH_EMAIL_FROM_NAME`
- `OFFERSTEADY_AUTH_GLOBAL_PASSWORD_MIN_LENGTH`
- `OFFERSTEADY_AUTH_GLOBAL_PASSWORD_MAX_LENGTH`
- `OFFERSTEADY_AUTH_GLOBAL_LOGIN_ATTEMPT_LIMIT`
- `OFFERSTEADY_AUTH_GLOBAL_LOGIN_WINDOW_SECONDS`
- `OFFERSTEADY_ADMIN_ENABLED`
- `OFFERSTEADY_ADMIN_ALLOWED_ORIGINS`
- `OFFERSTEADY_ADMIN_SESSION_TTL_SECONDS`
- `OFFERSTEADY_ADMIN_RECENT_MFA_TTL_SECONDS`
- `OFFERSTEADY_ADMIN_MAX_PAGE_SIZE`
- `OFFERSTEADY_ADMIN_QUERY_TIMEOUT_MS`
- `OFFERSTEADY_ADMIN_RATE_LIMIT_PER_MINUTE`
- `OFFERSTEADY_ADMIN_MAX_CONCURRENT_QUERIES`
- `OFFERSTEADY_PROMOTION_ENABLED`
- `OFFERSTEADY_PROMOTION_PUBLIC_BASE_URL`（可选；未设置时自动使用 `OFFERSTEADY_PUBLIC_WEB_BASE_URL`）
- `OFFERSTEADY_PROMOTION_ATTRIBUTION_WINDOW_DAYS`
- `OFFERSTEADY_PROMOTION_VISITOR_COOKIE_DAYS`
- `OFFERSTEADY_PROMOTION_TOUCHPOINT_RETENTION_DAYS`
- `OFFERSTEADY_PROMOTION_REPORTING_TIMEZONE`
- `OFFERSTEADY_PROMOTION_QUALIFICATION_MIN_VISIBLE_MS`
- `OFFERSTEADY_PROMOTION_REDIS_STREAM`
- `OFFERSTEADY_PROMOTION_REDIS_STREAM_MAXLEN`
- `OFFERSTEADY_PROMOTION_QUEUE_TIMEOUT_MS`
- `OFFERSTEADY_PROMOTION_INGEST_INTERVAL_SECONDS`：推广事件消费周期，默认 `10` 秒；重聚合仍独立按 300 秒执行
- `OFFERSTEADY_INTEGRATION_ENVIRONMENT_LABEL`
- `OFFERSTEADY_INTEGRATION_REPORT_OUTPUT_DIR`
- `OFFERSTEADY_INTEGRATION_HTTP_TIMEOUT_SECONDS`
- `OFFERSTEADY_INTEGRATION_RETRY_ATTEMPTS`
- `OFFERSTEADY_INTEGRATION_REALTIME_ASR_PROTOCOL`
- `OFFERSTEADY_INTEGRATION_MINERU_BASE_URL`
- `OFFERSTEADY_INTEGRATION_MINERU_PARSE_PATH`
- `OFFERSTEADY_INTEGRATION_MINERU_RESULT_PATH`
- `OFFERSTEADY_INTEGRATION_MINERU_MARKDOWN_FIELD`
- `OFFERSTEADY_INTEGRATION_MINERU_STATUS_FIELD`
- `OFFERSTEADY_INTEGRATION_MINERU_TASK_ID_FIELD`
- `OFFERSTEADY_INTEGRATION_MINERU_POLL_ATTEMPTS`
- `OFFERSTEADY_INTEGRATION_MINERU_POLL_INTERVAL_MS`
- `OFFERSTEADY_CHAT_QWEN_BASE_URL`
- `OFFERSTEADY_CHAT_DETAIL_RETRIEVAL_PREFETCH_ENABLED`：快答期间预取详细回答检索，默认开启
- `OFFERSTEADY_SCREENSHOT_VISION_BASE_URL`
- `OFFERSTEADY_SCREENSHOT_VISION_DELIVERY_MODE`：`inline`（默认，不写 OSS）或 `oss`（兼容回滚模式）
- `OFFERSTEADY_SCREENSHOT_VISION_STREAMING_ENABLED`：优先使用视觉模型流式响应，异常时回退完整响应
- `OFFERSTEADY_SCREENSHOT_VISION_ENABLE_THINKING`：截图视觉模型是否启用思考模式，默认 `false` 以缩短首个可见正文等待；只影响截图视觉请求
- `OFFERSTEADY_SCREENSHOT_PROGRESS_EMIT_INTERVAL_MS`：截图答案进度事件最小间隔，默认 `120` 毫秒
- `OFFERSTEADY_EMBEDDING_BASE_URL`
- `OFFERSTEADY_EMBEDDING_MODEL`
- `OFFERSTEADY_EMBEDDING_DIMENSION`
- `OFFERSTEADY_RERANK_BASE_URL`
- `OFFERSTEADY_RERANK_MODEL`
- `OFFERSTEADY_RERANK_API_PATH`
- `OFFERSTEADY_RAG_CONTEXT_MAX_CHUNKS`
- `OFFERSTEADY_RAG_CONTEXT_MAX_CHARACTERS`
- `OFFERSTEADY_RAG_CONTEXT_ALLOW_FULL_DOCUMENT`
- `OFFERSTEADY_REALTIME_ASR_BASE_URL`
- `OFFERSTEADY_REALTIME_ASR_WS_URL`
- `OFFERSTEADY_REALTIME_ASR_MODEL`
- `OFFERSTEADY_REALTIME_ASR_PROTOCOL`：`qwen3-realtime` 使用旧 `/api-ws/v1/realtime` 会话协议；`qwen-audio-task` 使用 Qwen Audio 3 的 `/api-ws/v1/inference` 任务协议。协议、模型和入口必须作为同一个回滚单元修改。
- `OFFERSTEADY_REALTIME_ASR_INFERENCE_WS_URL`：Qwen Audio 3 Streaming 的任务协议入口。当前验证通过的是 `wss://dashscope.aliyuncs.com/api-ws/v1/inference`；Workspace 专属入口仍返回 `Endpoint.AccessDenied`，未经重新验证不得用于生产。
- `OFFERSTEADY_REALTIME_ASR_MAX_SENTENCE_SILENCE_MS`：Qwen Audio 3 服务端 VAD 句尾静音阈值，默认 `300` 毫秒，服务端适配器限制为 `200–6000` 毫秒。该参数只缩短句尾 Final 判定，不控制讲话过程中的 Partial 返回频率；继续降低可能切碎自然停顿。
- `OFFERSTEADY_REALTIME_ASR_CONTINUOUS_TASK_ENABLED`：实验性 Qwen Audio task 跨本地话语复用，默认关闭。生产保持同一声道 WebSocket 长连接，但每句话执行独立 `finish-task → run-task`；当前模型持续 task 空闲约 23 秒会返回 `CLIENT_ERROR request timeout`，未经重新验证不得开启。
- `OFFERSTEADY_REALTIME_ASR_CONTINUOUS_TASK_SENTENCE_WAIT_SECONDS`：连续 task 等待 Provider `sentence_end` 的短暂宽限，默认 `0.65` 秒；超时立即进入兼容 task 轮换，不无限等待。
- `OFFERSTEADY_REALTIME_ASR_REPLAY_TAIL_MS`：Provider 断线时每个声道保留的滚动 PCM 尾部，默认 `2000` 毫秒；仅驻留后端进程内，并受 `OFFERSTEADY_REALTIME_ASR_REPLAY_BUFFER_MAX_BYTES` 上限约束。
- `OFFERSTEADY_REALTIME_ASR_WORKSPACE_ID`：百炼业务空间 ID；配置后 Qwen Realtime 优先连接该空间对应的地域专属域名。该值只配置在服务端，不下发客户端。
- `OFFERSTEADY_REALTIME_ASR_WORKSPACE_REGION`：Workspace 地域，默认 `cn-beijing`；必须与 API Key 和业务空间所属地域一致。
- `OFFERSTEADY_REALTIME_ASR_PERSISTENT_SESSIONS_ENABLED`：同一面试同一声道跨话语复用 Qwen WebSocket，生产默认开启
- `OFFERSTEADY_REALTIME_ASR_NONBLOCKING_PARTIALS_ENABLED`：非最终帧发送后不等待供应商 partial
- `OFFERSTEADY_REALTIME_ASR_COMMIT_SILENCE_MS`：Manual Commit 前追加的零 PCM 毫秒数，默认 `0`（关闭），服务端强制限制为 `0–160`；仅用于隔离尾词延迟实验，未经真实验收不得在生产开启
- `OFFERSTEADY_REALTIME_ASR_PREWARM_ENABLED`：进入正式面试后预热麦克风和系统音频 ASR 会话，默认开启
- `OFFERSTEADY_REALTIME_ASR_PREWARM_WAIT_SECONDS`：进入正式面试时等待双声道并行 ASR 预热完成的最长秒数，默认 `2.5`；超时后继续进入并使用惰性连接兜底
- `OFFERSTEADY_REALTIME_ASR_POINTS_PER_MINUTE`：实时面试每个会话分钟的积分价格，默认 `5`；会员有效时不扣积分
- `OFFERSTEADY_REALTIME_ASR_WORKER_COUNT`：实时 ASR 网络任务工作线程数，默认 `8`；入口仍受每会话有界队列保护
- `OFFERSTEADY_REALTIME_COLD_PATH_WORKER_COUNT`：最终历史、用量与上下文异步写入线程数，默认 `2`
- `OFFERSTEADY_REALTIME_COLD_PATH_QUEUE_MAX`：冷路径待处理任务上限，默认 `256`；达到上限时丢弃非关键异步工作，不能反压音频热路径
- `OFFERSTEADY_REALTIME_EVENT_BLOCK_MS`：Redis 会话事件阻塞等待上限，默认 `1000` 毫秒
- `OFFERSTEADY_REALTIME_EVENT_WAIT_WORKERS`：隔离 Redis 阻塞事件等待的专用线程数，默认 `32`；避免实时长连接占满普通 API 使用的通用执行器
- `OFFERSTEADY_REALTIME_DESKTOP_HEARTBEAT_TTL_SECONDS`：桌面助手在线租约时长，默认 `15` 秒
- `OFFERSTEADY_REALTIME_DESKTOP_HEARTBEAT_WRITE_MIN_INTERVAL_SECONDS`：设备信息未变化时写入心跳存储的最小间隔，默认 `10` 秒；实际间隔自动限制在 TTL 的一半以内，连续心跳仍立即返回最新在线状态
- `OFFERSTEADY_REALTIME_WEB_HEARTBEAT_TTL_SECONDS`：面试网页在线租约时长，默认 `15` 秒
- `OFFERSTEADY_LIVE_TASK_RUNTIME_TTL_SECONDS`：临时回答和截图任务 Redis 保留时间，默认 `7200` 秒
- `OFFERSTEADY_LIVE_TASK_STALE_SECONDS`：活跃任务无更新后的中断判定时间，默认 `180` 秒
- `OFFERSTEADY_RUNTIME_PERFORMANCE_TELEMETRY_ENABLED`：记录不含内容的全链路耗时阶段
- `OFFERSTEADY_RUNTIME_PERFORMANCE_TELEMETRY_TTL_SECONDS`：性能阶段记录保留时间，默认 7 天
- `OFFERSTEADY_RUNTIME_PERFORMANCE_TELEMETRY_SAMPLE_RATE`：性能记录采样率，范围 `0` 到 `1`
- `OFFERSTEADY_RUNTIME_PERFORMANCE_ACK_SESSION_CACHE_SECONDS`：字幕渲染性能确认的会话归属短缓存时长，默认 60 秒；仅用于无内容遥测授权校验
- `OFFERSTEADY_MZFPAY_BASE_URL`
- `OFFERSTEADY_MZFPAY_SUBMIT_PATH`
- `OFFERSTEADY_MZFPAY_NOTIFY_URL`
- `OFFERSTEADY_MZFPAY_RETURN_URL`
- `OFFERSTEADY_MZFPAY_PAYMENT_TTL_SECONDS`
- `OFFERSTEADY_CHECKOUT_PROVIDER`
- `OFFERSTEADY_ALIPAY_GATEWAY_URL`
- `OFFERSTEADY_ALIPAY_APP_ID`
- `OFFERSTEADY_ALIPAY_SELLER_ID`
- `OFFERSTEADY_ALIPAY_NOTIFY_URL`
- `OFFERSTEADY_ALIPAY_RETURN_URL`
- `OFFERSTEADY_ALIPAY_PAYMENT_TTL_SECONDS`

## 支付宝官方支付

当前版本的新订单渠道不再由 `OFFERSTEADY_CHECKOUT_PROVIDER` 单选控制，而是在运营后台“支付设置”中独立配置和启停；旧环境变量只保留用于历史 MZFPay 兼容及开发测试。完整操作和真实小额验收见 [`payment-channel-operations.md`](./payment-channel-operations.md)。

取得个体工商户资质、支付宝商家认证、网页应用审核和电脑网站支付签约后，将生产配置切换为：

```bash
OFFERSTEADY_CHECKOUT_PROVIDER=alipay
OFFERSTEADY_ALIPAY_GATEWAY_URL=https://openapi.alipay.com/gateway.do
OFFERSTEADY_ALIPAY_APP_ID=<开放平台应用 APPID>
OFFERSTEADY_ALIPAY_APP_PRIVATE_KEY=<RSA2 应用私钥>
OFFERSTEADY_ALIPAY_PUBLIC_KEY=<支付宝公钥>
OFFERSTEADY_ALIPAY_SELLER_ID=<签约商户 PID>
OFFERSTEADY_ALIPAY_NOTIFY_URL=https://mianshiwen.cn/api/v1/billing/payment-providers/alipay/notify
OFFERSTEADY_ALIPAY_RETURN_URL=https://mianshiwen.cn/app/billing
```

应用私钥和支付宝公钥只能注入后端密钥环境。浏览器返回地址只负责回到收费页，不能确认到账；权益发放必须以异步通知 RSA2 验签、应用与卖家身份、金额和交易状态全部通过为准。切换只影响新订单，历史 MZFPay 订单继续按其 `provider` 处理；需要回滚时只将 `OFFERSTEADY_CHECKOUT_PROVIDER` 恢复为 `mzfpay`。

审批完成前保持 `OFFERSTEADY_CHECKOUT_PROVIDER=` 为空。此时商品、积分、会员和历史订单仍可查询，但系统不会创建新的支付订单。

## 前端公开变量

- `VITE_APP_ENV`
- `VITE_API_BASE_URL`
- `VITE_PUBLIC_APP_VERSION`
- `VITE_GLOBAL_LOCALE`：仅供 `apps/web-global` 使用，可选 `en-US`、`en-GB`、`en-AU`、`en-CA`；默认 `en-US`
- `VITE_GLOBAL_COMMERCE_ENABLED`：仅供 `apps/web-global` 使用；国际支付、币种、税务和退款链路完成前必须保持 `false`
- `OFFERSTEADY_PRODUCT_EDITION`：后端产品边界，默认 `cn`；仅海外独立部署设为 `global`。
- `OFFERSTEADY_GLOBAL_COMMERCE_ENABLED`：服务端新结账总开关，默认 `false`。关闭时仍允许已发生订单的签名 Webhook 与对账处理。
- `OFFERSTEADY_GLOBAL_COMMERCE_PROVIDER_MODE`：`test` 或 `live`；两套密钥、映射、事件和启用状态不得混用。
- `OFFERSTEADY_CREEM_TEST_API_KEY` / `OFFERSTEADY_CREEM_LIVE_API_KEY`：仅服务端注入，禁止放入 `VITE_`、日志、响应或后台表单。
- `OFFERSTEADY_CREEM_TEST_WEBHOOK_SECRET` / `OFFERSTEADY_CREEM_LIVE_WEBHOOK_SECRET`：用于对原始请求体校验 `creem-signature`，仅服务端注入。
- `OFFERSTEADY_CREEM_CHECKOUT_SUCCESS_URL`：Creem 支付完成后的站内返回页；返回页只查询后端订单状态，不能发放权益。
- `OFFERSTEADY_CREEM_TEST_BASE_URL` / `OFFERSTEADY_CREEM_LIVE_BASE_URL`：Creem Test/Live API 地址，默认使用官方地址。
- `OFFERSTEADY_CREEM_HTTP_TIMEOUT_SECONDS` / `OFFERSTEADY_CREEM_HTTP_RETRY_ATTEMPTS`：服务端调用的有界超时与安全重试参数；退款等非幂等操作不自动重试。
- `OFFERSTEADY_GLOBAL_TERMS_URL` / `OFFERSTEADY_GLOBAL_PRIVACY_URL` / `OFFERSTEADY_GLOBAL_REFUND_POLICY_URL` / `OFFERSTEADY_GLOBAL_FAIR_USE_POLICY_URL`：Live 激活前必须配置的英文法律与支持页面。

Global 伴随程序打包还需要两个公开地址：

- `OFFERSTEADY_GLOBAL_WEB_URL`：独立 Global Web HTTPS 地址
- `OFFERSTEADY_GLOBAL_API_BASE_URL`：独立 Global API HTTPS 地址，必须指向版本化 API 根路径，例如 `https://offersteady.com/api/v1`

Global 打包脚本会拒绝国内生产域名。这两个变量只允许包含公开 URL，不得携带令牌或密钥。

前端只允许读取 `VITE_` 前缀变量，不得读取 OSS、数据库或服务端密钥。产品运行时不再支持 `VITE_APP_DATA_SOURCE=fixture` 或 strict/fallback 开关；页面数据统一来自 `VITE_API_BASE_URL` 指向的 Backend API。

## 本地启动建议

1. 复制 `.env.example` 为 `.env.local`
2. 补齐本地 PostgreSQL 与 OSS 测试配置
3. 如果联调微信兼容登录，再补齐 `OFFERSTEADY_ACCESS_TOKEN_SECRET`、`OFFERSTEADY_AUTH_WECHAT_APP_ID`、`OFFERSTEADY_AUTH_WECHAT_CALLBACK_URL`
4. Web 与 Backend 使用同一份环境语义，但前端只消费 `VITE_` 变量

认证用户和积分账本以PostgreSQL为唯一权威数据源。只要配置了 `OFFERSTEADY_DATABASE_URL`，认证和计费模块连接失败时会明确失败，不会退回内存仓库；这可以避免后端重启后用户身份变化、余额回到200点或重复发放新用户积分。纯单元测试可以直接构造内存服务，但不得将其作为已配置数据库环境的故障降级方案。

## v0.1 服务器部署补充

服务器部署使用 `.env.production` 或部署平台 secret 注入，不能提交 Git。推荐先复制 `.env.example`，再替换真实值：

```bash
cp .env.example .env.production
chmod 600 .env.production
```

服务器公网地址为 `101.133.147.212` 且暂未配置 HTTPS 时，内测示例：

```bash
OFFERSTEADY_ENV=production
OFFERSTEADY_PUBLIC_WEB_BASE_URL=http://101.133.147.212
OFFERSTEADY_CORS_ALLOWED_ORIGINS=["http://101.133.147.212"]
VITE_APP_ENV=production
VITE_API_BASE_URL=http://101.133.147.212
VITE_PUBLIC_APP_VERSION=0.1.0
OFFERSTEADY_MZFPAY_NOTIFY_URL=https://mianshiwen.cn/api/v1/billing/payment-providers/mzfpay/notify
OFFERSTEADY_MZFPAY_RETURN_URL=https://mianshiwen.cn/app/billing
```

如果后续绑定域名和 HTTPS，将上述 URL 统一替换为 `https://<domain>`。码支付真实自动到账必须使用公网可访问的 `OFFERSTEADY_MZFPAY_NOTIFY_URL`，不能使用 `127.0.0.1`、`localhost` 或局域网地址。

Docker Compose 启动示例：

```bash
docker compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --build
```

Web 镜像在构建期读取 `VITE_API_BASE_URL`，因此修改前端 API 地址后需要重新构建 Web 镜像。

v0.1 默认只允许管理员/内部账号小额验证码支付链路。支付订单、积分流水和会员权益完成持久化前，不应开放真实付费用户。

## 商业化资料与 RAG 补充

Prompt版本由`OFFERSTEADY_CHAT_PROMPT_TEMPLATE_PATH`、`OFFERSTEADY_CHAT_PROMPT_VERSION`、`OFFERSTEADY_SCREENSHOT_PROMPT_TEMPLATE_PATH`和`OFFERSTEADY_SCREENSHOT_PROMPT_VERSION`控制。默认使用Chat v4和Screenshot v2；上一稳定版本分别为`system-v3.md`/v3和`system-v1.md`/v1。原始Prompt、资料、截图和完整回答不得写入日志。

截图视觉传输默认使用 `OFFERSTEADY_SCREENSHOT_VISION_DELIVERY_MODE=inline`：服务端校验和压缩后，以临时 Data URL 调用视觉模型，不把截图保存到 OSS。只有模型供应商不兼容内联图片或需要紧急回滚时才切换为 `oss`；该变量仅在服务端读取，修改后需重启后端。

资料上传、解析、索引和 RAG 只由后端读取服务端变量。浏览器只能拿到上传意图、资料状态和安全来源摘要，不能读取 OSS 密钥、数据库连接串、完整对象路径策略、Embedding/Rerank/Chat 密钥或 Prompt。

OSS 路径由以下变量共同决定：

- `OFFERSTEADY_OSS_KEY_PREFIX`：产品级对象前缀，例如 `materials`
- `OFFERSTEADY_OSS_ENVIRONMENT_LABEL`：环境隔离标签，例如 `development`、`staging`、`production`
- `OFFERSTEADY_MATERIAL_USER_HASH_SALT`：服务端私有盐，用于生成不可逆用户路径标识，不能进入前端或日志

资料限制由以下变量控制：

- `OFFERSTEADY_MATERIAL_MAX_FILE_SIZE_BYTES`
- `OFFERSTEADY_MATERIAL_MAX_PAGE_COUNT`
- `OFFERSTEADY_MATERIAL_MAX_TEXT_CHARACTERS`
- `OFFERSTEADY_MATERIAL_SUPPORTED_EXTENSIONS`

资料任务执行由以下变量控制：

- `OFFERSTEADY_DOCUMENT_PROCESSING_INLINE_WORKER_ENABLED`：仅用于开发兼容；生产 API 必须为 `false`，资料解析由独立 `material-worker` 执行。
- `OFFERSTEADY_DOCUMENT_PROCESSING_JOB_LEASE_SECONDS`：Worker 任务租约，默认 900 秒；Worker 异常退出后，超出租约的任务会安全重新排队。

生产环境的上传凭证、处理任务和处理事件均写入 PostgreSQL。API 发布或 Worker 重启不得依赖进程内队列恢复资料任务。

RAG 运行边界由以下变量控制：

- `OFFERSTEADY_EMBEDDING_MODEL`
- `OFFERSTEADY_EMBEDDING_DIMENSION`
- `OFFERSTEADY_RERANK_MODEL`
- `OFFERSTEADY_RAG_CONTEXT_MAX_CHUNKS`
- `OFFERSTEADY_RAG_CONTEXT_MAX_CHARACTERS`
- `OFFERSTEADY_RAG_CONTEXT_ALLOW_FULL_DOCUMENT`

生产建议：

- `OFFERSTEADY_RAG_CONTEXT_ALLOW_FULL_DOCUMENT` 默认保持 `false`
- `.env` / `.env.local` 可以放本地测试值，但生产密钥应进入部署平台或密钥管理系统
- 集成测试只使用合成或脱敏资料，不能上传真实候选人简历、真实 JD 或真实知识库原文

## 微信兼容登录补充

- `OFFERSTEADY_AUTH_WECHAT_PROVIDER_MODE=compatible` 表示当前开发联调阶段由后端生成兼容正式流程的授权会话，并允许开发环境完成扫码/授权模拟。
- `OFFERSTEADY_AUTH_WECHAT_PROVIDER_MODE=formal` 预留给正式微信开放平台接入；此时应由服务端根据正式提供方返回授权入口和回调结果。
- `OFFERSTEADY_AUTH_WECHAT_APP_SECRET` 仅允许保存在服务端或密钥管理系统，浏览器和 `VITE_` 变量中都不能出现。
- `OFFERSTEADY_AUTH_WECHAT_AUTHORIZATION_TTL_SECONDS` 控制二维码/授权会话有效期，过期后必须重新创建授权会话。
- `OFFERSTEADY_AUTH_WECHAT_CALLBACK_URL` 必须与服务端部署域名一致，开发环境可以指向本地 backend 的 `/api/v1/auth/wechat/callback`。

## 短信验证码登录补充

- `OFFERSTEADY_AUTH_SMS_PROVIDER_MODE=fake` 用于本地开发和自动化测试，默认验证码由 `OFFERSTEADY_AUTH_SMS_FAKE_CODE` 控制，默认 `123456`。
- `OFFERSTEADY_AUTH_SMS_PROVIDER_MODE=aliyun` 时，后端通过阿里云号码认证服务 `Dypnsapi` 调用 `SendSmsVerifyCode` 和 `CheckSmsVerifyCode`。
- `OFFERSTEADY_AUTH_SMS_PROVIDER_MODE=aliyun-dysmsapi` 时，后端通过阿里云短信服务 `Dysmsapi SendSms` 发送验证码，并只保存带 `OFFERSTEADY_AUTH_SMS_CODE_PEPPER` 的 HMAC 摘要进行本地校验。
- 个人开发者应按阿里云“个人开发者如何接入短信验证码服务”流程开通短信认证；该流程不需要企业营业执照、不需要自定义企业短信签名或自定义模板。
- `OFFERSTEADY_AUTH_SMS_ALIYUN_SIGN_NAME` 填阿里云号码认证服务控制台赠送/预置的系统签名名称。
- `OFFERSTEADY_AUTH_SMS_ALIYUN_TEMPLATE_CODE` 填同一控制台赠送/预置的标准验证码模板编号。
- `OFFERSTEADY_AUTH_SMS_ALIYUN_ACCESS_KEY_ID` 与 `OFFERSTEADY_AUTH_SMS_ALIYUN_ACCESS_KEY_SECRET` 只能放在后端环境或密钥管理系统，不得进入浏览器、`VITE_` 变量或前端源码。
- 阿里云短信验证码由阿里云托管生成和校验，模板参数中的验证码占位使用 `##code##`；后端不生成、不保存、不记录验证码明文。
- Dysmsapi 模式的模板变量为 `code`；服务端使用安全随机数生成六位验证码，不保存或记录明文，`OFFERSTEADY_AUTH_SMS_CODE_PEPPER` 必须使用独立高强度随机值。
- `OFFERSTEADY_AUTH_SMS_SEND_INTERVAL_SECONDS` 不应低于 `60`；生产默认使用 60 秒，与阿里云验证码短信默认的同号码分钟级频控保持一致。渠道返回频控时，接口返回可纠正的 429 提示，不将其误报为服务不可用。
- 当前产品只支持中国大陆手机号，后端会以 `CountryCode=86` 调用阿里云接口。
- `OFFERSTEADY_AUTH_SMS_TEST_PHONE_NUMBER` 只用于显式运行真实短信集成验收，普通单元测试不得调用真实短信 API。
- 日志只允许记录手机号哈希、脱敏手机号、challenge id、provider request id、耗时和错误码，不能记录验证码明文。

## 海外邮箱验证码登录

- 邮箱认证默认关闭；只有海外独立部署设置 `OFFERSTEADY_AUTH_EMAIL_ENABLED=true` 后，邮箱接口才可用。国内环境保持关闭，不改变手机号登录。
- 自动化测试可使用 `OFFERSTEADY_AUTH_EMAIL_PROVIDER_MODE=fake` 和合成验证码。生产环境启用邮箱认证时必须使用 `smtp`，否则后端拒绝启动该认证配置，禁止降级到 fake。
- SMTP 生产配置至少需要 host、username、password、已验证的 from address 和独立高强度 `OFFERSTEADY_AUTH_EMAIL_CODE_PEPPER`。支持 587 + STARTTLS，也支持服务商要求的 465 隐式 TLS；隐式 TLS 时设置 `SMTP_SSL=true`、`SMTP_STARTTLS=false`。
- 国际版普通用户默认使用邮箱和密码登录。新密码采用 Argon2id；注册、老用户首次设密和找回密码继续复用用途隔离的一次性邮箱验证码。密码策略与失败次数窗口仅在 `OFFERSTEADY_PRODUCT_EDITION=global` 时生效。
- 发送域名上线前必须完成供应商验证，并配置 SPF、DKIM 和 DMARC。发件人名称默认 `OfferSteady`，实际发件地址由运营方确认。
- 验证码为六位随机数，数据库只保存 HMAC 摘要；challenge 只保存邮箱哈希与脱敏地址。日志不得记录完整邮箱、验证码或 SMTP 凭据。
- 默认验证码有效期 10 分钟、同邮箱 60 秒内不可重发、每日最多 20 次、最多验证 5 次。这些限制不替代供应商侧配额和网络层限流。
- 上线顺序：先以关闭状态部署加法迁移和后端，再配置并验证真实邮件发送，最后启用邮箱认证并发布 Global Web。失败时回滚 Global Web/Backend 镜像，新增表可保留且不会影响国内库。
- 生产冒烟测试必须覆盖：真实收件、错误码、过期码、重复使用、新账号、已有账号再次登录、刷新令牌、退出登录；测试邮箱必须为专用合成账号。

## 第三方集成验收补充

后端集成验收命令：

```bash
cd apps/backend
python -m app.services.integration_verification --list
python -m app.services.integration_verification
```

建议：

- 本地先只跑单项，例如 `--item oss`、`--item postgresql`
- 真实第三方调用会产生费用，尤其是 Chat、Vision、Embedding、Rerank、Realtime ASR
- Integration Report 默认输出到 `artifacts/integration-reports/`

全链路联调命令：

```bash
cd apps/backend
python -m app.services.end_to_end_integration --skip-providers
python -m app.services.end_to_end_integration
```

前端联调模式：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev:web
```

实时问答模型联调补充：

- `OFFERSTEADY_CHAT_QWEN_BASE_URL` 应填写 OpenAI-compatible 根地址，例如 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
- `OFFERSTEADY_CHAT_QWEN_API_KEY` 只放在服务端 `.env`，不要放进任何 `VITE_` 前端变量。
- `OFFERSTEADY_CHAT_QWEN_MODEL` 与当前百炼 / DashScope 控制台可用模型名保持一致。
- `OFFERSTEADY_CHAT_QUICK_MODEL` 可选；配置后仅实时快答、问题规范化与快答续写使用该模型。留空即可回退到共享模型。当前候选值为 `deepseek-v4.1-flash`。
- `OFFERSTEADY_CHAT_DETAIL_MODEL` 可选；配置后仅实时详细回答、详细回答语言修复与详细续写使用该模型。留空即可回退到 `OFFERSTEADY_CHAT_QWEN_MODEL`。文档摘要、通用非实时对话及其他 AI 链路不受影响。当前候选值为 `deepseek-v4.1-flash`。
- `OFFERSTEADY_WEB_SEARCH_ENABLED` 默认关闭；仅在服务端配置并验证 Responses API 后开启联网详细回答。
- `OFFERSTEADY_WEB_SEARCH_RESPONSES_BASE_URL` 应填写百炼业务空间的 Responses API 根地址（北京或新加坡地域），不得暴露到前端。
- `OFFERSTEADY_WEB_SEARCH_API_KEY` 可单独配置联网密钥；留空时回退使用服务端聊天密钥。
- `OFFERSTEADY_WEB_SEARCH_TIMEOUT_SECONDS` 默认 2.5 秒；联网超时会回退到本地知识库，不阻断普通回答。
- `OFFERSTEADY_WEB_SEARCH_MAX_SOURCES`、`OFFERSTEADY_WEB_SEARCH_MAX_CONTEXT_CHARACTERS` 分别限制来源数和证据上下文长度。
- `OFFERSTEADY_WEB_SEARCH_POINTS` 默认 20，仅由服务端计费逻辑读取。
- `VITE_API_BASE_URL` 推荐填写后端根地址 `http://127.0.0.1:8000`；如果本地误写成 `http://127.0.0.1:8000/api/v1`，前端运行时会归一化为后端根地址，避免请求被拼成重复 `/api/v1/api/v1/...`。
- 后端配置读取会优先使用仓库根目录 `.env` / `.env.local`，因此从项目根目录或 `apps/backend` 目录启动后端联调脚本都能读取同一份本地配置。
