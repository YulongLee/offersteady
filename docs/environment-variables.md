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
- `OFFERSTEADY_ADMIN_ENABLED`
- `OFFERSTEADY_ADMIN_ALLOWED_ORIGINS`
- `OFFERSTEADY_ADMIN_SESSION_TTL_SECONDS`
- `OFFERSTEADY_ADMIN_RECENT_MFA_TTL_SECONDS`
- `OFFERSTEADY_ADMIN_MAX_PAGE_SIZE`
- `OFFERSTEADY_ADMIN_QUERY_TIMEOUT_MS`
- `OFFERSTEADY_ADMIN_RATE_LIMIT_PER_MINUTE`
- `OFFERSTEADY_ADMIN_MAX_CONCURRENT_QUERIES`
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
- `OFFERSTEADY_REALTIME_ASR_WORKSPACE_ID`：百炼业务空间 ID；配置后 Qwen Realtime 优先连接该空间对应的地域专属域名。该值只配置在服务端，不下发客户端。
- `OFFERSTEADY_REALTIME_ASR_WORKSPACE_REGION`：Workspace 地域，默认 `cn-beijing`；必须与 API Key 和业务空间所属地域一致。
- `OFFERSTEADY_REALTIME_ASR_PERSISTENT_SESSIONS_ENABLED`：同一面试同一声道跨话语复用 Qwen WebSocket，生产默认开启
- `OFFERSTEADY_REALTIME_ASR_NONBLOCKING_PARTIALS_ENABLED`：非最终帧发送后不等待供应商 partial
- `OFFERSTEADY_REALTIME_ASR_PREWARM_ENABLED`：进入正式面试后预热麦克风和系统音频 ASR 会话，默认开启
- `OFFERSTEADY_REALTIME_ASR_PREWARM_WAIT_SECONDS`：进入正式面试时等待双声道并行 ASR 预热完成的最长秒数，默认 `2.5`；超时后继续进入并使用惰性连接兜底
- `OFFERSTEADY_REALTIME_ASR_POINTS_PER_MINUTE`：实时面试每个会话分钟的积分价格，默认 `5`；会员有效时不扣积分
- `OFFERSTEADY_REALTIME_ASR_WORKER_COUNT`：实时 ASR 网络任务工作线程数，默认 `8`；入口仍受每会话有界队列保护
- `OFFERSTEADY_REALTIME_COLD_PATH_WORKER_COUNT`：最终历史、用量与上下文异步写入线程数，默认 `2`
- `OFFERSTEADY_REALTIME_COLD_PATH_QUEUE_MAX`：冷路径待处理任务上限，默认 `256`；达到上限时丢弃非关键异步工作，不能反压音频热路径
- `OFFERSTEADY_REALTIME_EVENT_BLOCK_MS`：Redis 会话事件阻塞等待上限，默认 `1000` 毫秒
- `OFFERSTEADY_REALTIME_EVENT_WAIT_WORKERS`：隔离 Redis 阻塞事件等待的专用线程数，默认 `32`；避免实时长连接占满普通 API 使用的通用执行器
- `OFFERSTEADY_LIVE_TASK_RUNTIME_TTL_SECONDS`：临时回答和截图任务 Redis 保留时间，默认 `7200` 秒
- `OFFERSTEADY_LIVE_TASK_STALE_SECONDS`：活跃任务无更新后的中断判定时间，默认 `180` 秒
- `OFFERSTEADY_RUNTIME_PERFORMANCE_TELEMETRY_ENABLED`：记录不含内容的全链路耗时阶段
- `OFFERSTEADY_RUNTIME_PERFORMANCE_TELEMETRY_TTL_SECONDS`：性能阶段记录保留时间，默认 7 天
- `OFFERSTEADY_RUNTIME_PERFORMANCE_TELEMETRY_SAMPLE_RATE`：性能记录采样率，范围 `0` 到 `1`
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
- `VITE_API_BASE_URL` 推荐填写后端根地址 `http://127.0.0.1:8000`；如果本地误写成 `http://127.0.0.1:8000/api/v1`，前端运行时会归一化为后端根地址，避免请求被拼成重复 `/api/v1/api/v1/...`。
- 后端配置读取会优先使用仓库根目录 `.env` / `.env.local`，因此从项目根目录或 `apps/backend` 目录启动后端联调脚本都能读取同一份本地配置。
