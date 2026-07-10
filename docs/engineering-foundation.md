# 生产级基础工程约定

## 仓库分层

- `apps/web`: React + TypeScript 前端
- `apps/backend`: FastAPI 后端主线
- `apps/api`: 原型参考服务，不再作为正式主线扩展
- `packages/protocol`: 前后端共享协议
- `packages/config`: 公开环境变量键、运行时配置读取和日志字段约定
- `infra/`: Docker、Compose、Nginx、PostgreSQL 初始化资产
- `ai/`: Prompt、评测与脱敏样本
- `tests/`: 跨应用集成和端到端测试

## 后端模块规范

后端统一按以下职责扩展：

- `app/api/routers/`: 跨模块或平台级路由
- `app/modules/`: 业务功能路由入口与模块描述
- `app/schemas/`: 请求、响应和平台模型
- `app/services/`: 用例编排与状态机
- `app/adapters/`: OSS、数据库、供应商等基础设施实现
- `app/platform/`: 数据库、pgvector、对象存储、迁移等运行时边界
- `app/middleware/`: request-id、日志、CORS 等横切能力
- `app/core/`: 配置、响应壳、异常和日志基础设施

## Document Service 约束

统一 Document Service 负责：

- 上传意图签发
- OSS 唯一对象键生成
- 文档元数据登记
- 文档状态流转
- 文档列表与删除
- 权限边界

统一 Document Service 不负责：

- 解析原始文档
- 生成 Markdown
- Chunk / Embedding
- 向量写入
- RAG 检索

这些后续能力应通过独立的 Document Processing Pipeline 接入，并只消费文档服务暴露的受控交接状态。

## Web 原型完整性

当前项目仍以产品原型验证为先，因此 `apps/web` 中已被用户确认的页面结构、文案表达和交互顺序应视为受保护基线。

约束如下：

- 后端联调或协议升级不得默认改变已批准的原型表现
- 如需接入新后端能力，应优先通过 adapter 或兼容层完成
- 若为保持编译通过必须保留兼容字段，只允许保留最小兼容，不应顺势改动原型行为

本地恢复或 review Web 原型时，至少按以下顺序验证：

1. `npm run typecheck -w @offersteady/web`
2. `npm run test -w @offersteady/web`
3. `npm run build -w @offersteady/web`
4. 启动本地 Web 预览服务后，再运行 `npm run review:live -w @offersteady/web`

注意：`review:live` 依赖浏览器访问中的 Web 页面；若预览服务未启动，脚本会把“服务不可达”表现为页面审查失败，不能直接作为页面回归结论。

如需快速判断“网页访问不了”是否只是本地服务未起或地址不对，优先运行 `npm run doctor:web`。当前约定：

- `npm run dev:web` → 默认访问 `http://127.0.0.1:5173/`
- `npm run preview:web` → 默认访问 `http://127.0.0.1:4173/`
- `review:live` 会自动探测环境变量地址、4173 和 5173，再决定是否执行页面巡检

## 统一 API 响应

后端成功与失败都使用同一顶层结构：

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

错误响应保持同样的顶层字段，只是 `success=false` 且 `error` 填充 `code/message/details`。

## 日志基线

结构化日志最少包含：

- `timestamp`
- `level`
- `service`
- `environment`
- `event`
- `request_id`
- `feature`
- `action`
- `error_code`

不得记录简历正文、JD 正文、知识库原文、截图内容和长期凭证。

## 第三方集成验收线

当前工程额外提供一条独立的第三方集成验收能力，专门验证以下外部依赖是否真实可用：

- Aliyun OSS
- MinerU
- Qwen-compatible Chat
- Qwen-compatible Vision
- Embedding Provider
- Rerank Provider
- Realtime ASR Provider
- PostgreSQL
- pgvector

约束如下：

- 不改动已批准的 Web 原型页面和交互
- 所有验证都必须走真实 API / 真实基础设施连接
- 输入材料必须使用合成或脱敏样本
- 输出统一 Integration Report（JSON + Markdown）
- 日志只允许记录脱敏摘要、耗时、状态和错误码，不能输出长期密钥或原始敏感内容
