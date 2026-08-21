## Context

当前桌面助手已把屏幕截图压缩为最长边 1600px、质量 72 的 JPEG，并通过既有 multipart 接口上传到 FastAPI。后端再次校验和优化后，一方面把字节保存在进程内上传端口，另一方面同步写入 OSS；预处理器优先生成 OSS 签名 URL，视觉模型适配器也已具备在没有 URL 时使用 `data:<mime>;base64,...` 的能力。

历史受控样本中 OSS 正常写入约 3 秒，异常可超过 15 秒，而截图不是用户需要保留的业务资料。该步骤既增加端到端等待，也扩大敏感截图的留存范围。桌面端不得直接调用视觉供应商，因为模型密钥只能保存在服务端。

## Goals / Non-Goals

**Goals:**

- 默认从截图回答链路移除 OSS 写入和签名 URL 生成。
- 复用现有压缩、校验、任务状态、视觉 Prompt、答案、计费和会话事件行为。
- 图片只在后台任务所需的最短生命周期内存在，日志和事件仅保留尺寸、字节数、哈希、耗时和传输模式等元数据。
- 允许通过服务端配置切回 OSS 模式，降低供应商兼容或上线异常的回滚成本。

**Non-Goals:**

- 不让桌面助手持有视觉模型密钥或直接访问模型供应商。
- 不修改桌面截图分辨率、JPEG 质量、网页按钮或答案顺序。
- 不修改截图回答积分、视觉模型、Prompt 或重试次数。
- 本变更不解决截图任务仓储仍为进程内实现的问题。

## Decisions

### Decision 1: Add a server-side `inline` / `oss` delivery mode

新增截图视觉传输模式，默认 `inline`。`inline` 模式只创建进程内的确认上传记录，不调用对象存储；`oss` 模式保留当前写入对象并生成短时签名 URL 的行为。

Alternative: 只把现有 `screenshot_use_signed_url_for_vision` 设为 false。Rejected，因为当前 `upload_bytes` 无论该配置如何都会先写 OSS，无法达到“不保存截图”的目标。

### Decision 2: Keep the existing desktop-to-backend multipart boundary

桌面端继续上传压缩 JPEG，后端继续执行会话归属、MIME、大小和图像有效性校验。只有后端到视觉模型的一段改为 Base64 Data URL。

Alternative: 桌面端直接调用视觉模型。Rejected，因为会泄露服务端 API Key、绕过计费和会话校验，也难以统一取消与审计。

### Decision 3: Inline only optimized bytes and bound request size

视觉模型只接收最长边 1600px、质量 72 的优化结果。Base64 会增加约三分之一的传输体积，但现有实测压缩截图通常约 90–150KB，成本显著低于一次 OSS 写入和供应商二次下载。

Alternative: 传输原始 PNG。Rejected，因为请求体、模型视觉 token 和内存峰值更高。

### Decision 4: Preserve metadata, never image content

任务和阶段遥测记录 `delivery_mode`、压缩尺寸、字节数、耗时与失败阶段，不记录 Base64、原始图片或可访问 URL。任务完成、失败或取消后，上传端口必须释放对应图片字节。

Alternative: 依赖进程重启清理。Rejected，因为常驻进程会让截图在内存中不必要地累积。

## Risks / Trade-offs

- [Risk] 某些 OpenAI-compatible 视觉端点不接受 Data URL。→ Mitigation: 上线前运行真实供应商探针，并保留 `oss` 模式快速回滚。
- [Risk] Base64 增加约 33% 请求体。→ Mitigation: 继续执行双端 1600px/JPEG 72 优化，并沿用文件大小和图片数量上限。
- [Risk] 重试期间提前释放图片会导致第二次调用失败。→ Mitigation: 只在整个回答任务进入终态后释放，不在单次视觉尝试后释放。
- [Risk] 取消发生在后台任务执行期间。→ Mitigation: 保持当前取消语义，并在所有终态路径执行幂等清理。
- [Risk] 供应商仍可能按其政策处理输入图片。→ Mitigation: 产品隐私描述应区分“不保存到面试稳 OSS”和“模型供应商为完成请求而处理”。

## Migration Plan

1. 增加默认 `inline` 的服务端配置和兼容 `oss` 模式。
2. 调整截图上传服务，使 `inline` 模式跳过对象存储写入并输出对应遥测。
3. 为终态清理、无 OSS 调用、Data URL 调用和 OSS 回滚路径增加回归测试。
4. 运行真实视觉配置校验、截图专项测试和后端全量测试。
5. 仅重建并发布后端；桌面助手与网页不需要重新构建。
6. 上线后观察截图成功率、视觉模型耗时和总后台耗时；异常时设置传输模式为 `oss` 并重启后端。

## Open Questions

无。当前视觉网关和集成验证已经使用同一种 Data URL 格式，具备直接实施条件。
