# OfferSteady Backend Foundation

`apps/backend` 是 MVP 第一阶段的正式服务端基础工程，使用 FastAPI 搭建。

当前阶段只提供：

- 应用入口与健康检查
- `/api/v1` 版本化根路径
- 按功能域拆分的路由与平台级 `system` 路由
- 统一响应壳、异常翻译、request-id 和结构化日志
- PostgreSQL / pgvector / OSS 的运行时边界与健康基线
- 后续文件存储、解析、检索、生成与流式能力的扩展点

当前不提供真实业务逻辑。上传简历、JD、RAG、实时回答、截图回答等功能会在后续变更中逐步接入这里预留的模块。

当前资料上传 MVP 骨架已补充：

- 服务端签发短时 OSS 上传意图
- 客户端直传对象存储后再调用完成确认
- 简历、JD、知识资料共用一套格式校验 `pdf/docx/doc/txt/md`
- JD 粘贴文本保留为独立创建路径
- 新上传资料默认进入非就绪状态，不能立刻用于面试

当前还新增了一条独立的第三方集成验收线，用于真实验证：

- OSS 上传 / Head / 下载
- MinerU 文档解析
- Qwen-compatible Chat
- Qwen-compatible Vision
- Embedding
- Rerank
- Realtime ASR
- PostgreSQL
- pgvector

这条验收线不改变 Web 原型，也不走前端页面；它只在后端侧通过受控命令执行，并输出 Integration Report。

本地环境变量（开发/联调）：

- `OFFERSTEADY_OSS_BUCKET`
- `OFFERSTEADY_OSS_ENDPOINT`
- `OFFERSTEADY_OSS_REGION`
- `OFFERSTEADY_OSS_KEY_PREFIX`
- `OFFERSTEADY_OSS_ACCESS_KEY_ID`
- `OFFERSTEADY_OSS_ACCESS_KEY_SECRET`
- `OFFERSTEADY_OSS_UPLOAD_INTENT_TTL_SECONDS`
- `OFFERSTEADY_DATABASE_URL`
- `OFFERSTEADY_PGVECTOR_SCHEMA`
- `OFFERSTEADY_PGVECTOR_EXTENSION_NAME`
- `OFFERSTEADY_LOG_LEVEL`
- `OFFERSTEADY_REQUEST_ID_HEADER`

注意：

- 当前测试和原型联调只允许使用合成或脱敏资料，不要把真实简历、真实 JD 或真实知识材料放进测试夹具。
- 当前后端实现是内存版上传骨架，用于验证接口和状态边界，不代表生产级持久化与异步任务方案。
- 当前数据库与 pgvector 只建立连接、扩展和健康检查边界，不包含业务 repository。

统一响应结构：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "requestId": "req_xxx",
  "meta": {
    "apiVersion": "v1",
    "timestamp": "2026-06-30T00:00:00Z"
  }
}
```

平台级诊断接口：

- `/healthz`
- `/api/v1/system/foundation`
- `/api/v1/system/ownership`
- `/api/v1/system/runtime`

本地运行：

```bash
python3 -m uvicorn app.main:app --reload --app-dir apps/backend
```

运行测试：

```bash
PYTHONPATH=apps/backend pytest apps/backend/tests
```

运行第三方集成验收：

```bash
cd apps/backend
python -m app.services.integration_verification --list
python -m app.services.integration_verification
python -m app.services.integration_verification --item oss --item postgresql
```

或使用安装后的脚本：

```bash
offersteady-verify-integrations
```

运行全链路联调：

```bash
cd apps/backend
python -m app.services.end_to_end_integration --skip-providers
python -m app.services.end_to_end_integration
```

或使用安装后的脚本：

```bash
offersteady-run-e2e
```

默认报告输出目录：

```text
artifacts/integration-reports/<report-id>/
  report.json
  report.md
```

注意：

- 所有第三方验收都要求真实 API / 真实基础设施连接。
- 验证输入仅允许使用合成或脱敏样本，不要上传真实用户简历、真实 JD、真实截图或真实音频。
- 日志与报告会做脱敏摘要，不会输出长期密钥原文。
- Web 原型切到真实后端时，使用 `VITE_APP_DATA_SOURCE=api`、`VITE_APP_STRICT_API_ONLY=true` 与 `VITE_API_BASE_URL=http://127.0.0.1:8000`，不新增页面或交互分支。
