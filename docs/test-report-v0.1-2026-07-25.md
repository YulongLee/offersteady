# OfferSteady v0.1 全量测试报告

## 1. 报告信息

- 产品：面试稳 OfferSteady
- 测试日期：2026-07-25
- 测试版本：`af474c3`
- 线上地址：`https://mianshiwen.cn/`
- 线上环境：Ubuntu 24.04、Docker Compose、PostgreSQL 16、pgvector、Redis、Nginx/Caddy
- 测试数据：仅使用合成或脱敏数据
- 总体结论：**有条件通过，不建议直接作为面向公众的正式商业版本发布**

当前版本已经拉通 Web、Backend、OSS、MinerU、Embedding、Rerank、Chat、Vision、Realtime ASR、PostgreSQL、pgvector 和 Redis 等主要技术能力。资料处理、RAG 面试回答、截图回答和实时语音的后端编排可以完成。

当前仍存在桌面真实采集失败、部分运行状态未持久化、真实短信发送未验收、真实支付回调未验收以及缺少浏览器级 UI 验收等发布阻塞项。建议继续作为内部测试或受控 Beta 版本，不建议立即开放给不受控的真实付费用户。

## 2. 结果摘要

| 测试层级 | 结果 | 说明 |
| --- | --- | --- |
| Node 工作区自动化测试 | 通过 | 51 个测试文件，294 项测试全部通过 |
| FastAPI 自动化测试 | 通过 | 隔离真实供应商后 101 项通过，5 项条件跳过 |
| TypeScript 类型检查 | 通过 | API、Desktop、Web、Config、Protocol 全部通过 |
| 生产构建 | 通过 | Desktop、Web、共享包构建成功 |
| 第三方 AI 与存储集成 | 通过 | OSS、MinerU、Chat、Vision、Embedding、Rerank、Realtime ASR 均通过 |
| 线上数据库 | 通过 | PostgreSQL 连接与 pgvector 最近邻查询通过 |
| 安全 E2E 编排 | 通过 | 4/4 场景通过 |
| 线上服务与路由 | 通过 | 首页、登录、资料、面试、积分、说明、下载、隐私、条款路由均为 HTTP 200 |
| 桌面真实麦克风采集 | 失败 | `microphone-device-not-found`，未产生音频帧 |
| 桌面系统音频/屏幕采集 | 失败 | `screen-capture-permission-required`，未产生系统音频帧 |
| 真实短信发送与验证码登录 | 未执行 | 配置通过；为避免产生短信费用和向真实号码发送信息，未发送 |
| 真实码支付付款与异步回调 | 未执行 | 自动化契约通过；未进行真实付款、验签通知和权益到账验收 |
| 浏览器点击式 UI 验收 | 未执行 | 当前测试环境没有可连接的浏览器实例 |

## 3. 自动化测试

### 3.1 Node 工作区

执行命令：

```bash
npm test
npm run typecheck
npm run build
```

测试结果：

| 工作区 | 测试文件 | 测试项 | 结果 |
| --- | ---: | ---: | --- |
| API | 13 | 90 | 通过 |
| Desktop | 7 | 31 | 通过 |
| Web | 23 | 146 | 通过 |
| Protocol | 8 | 27 | 通过 |
| 合计 | 51 | 294 | 通过 |

Web 生产构建生成约 780 KB 的主 JavaScript Chunk，构建工具给出大于 500 KB 的警告。该问题不阻塞功能，但会影响首次加载性能，建议后续进行路由级代码拆分。

### 3.2 FastAPI

直接执行全量测试时，测试进程读取了仓库根目录真实 `.env`，导致单元测试意外调用阿里云短信和真实模型，初次结果为 92 项通过、9 项失败、5 项跳过。

将短信、Chat、Vision、Embedding、Rerank 和 MinerU 显式切换到隔离测试配置后，最终结果为：

- 101 项通过
- 0 项失败
- 5 项条件跳过
- 1 条 Starlette/httpx 弃用警告

这说明业务回归测试可通过，但测试环境隔离仍需修复。默认执行 `pytest` 不应读取真实生产供应商配置或产生真实 API 调用。

## 4. 第三方集成

| 集成 | 结果 | 实测耗时 | 说明 |
| --- | --- | ---: | --- |
| Aliyun OSS | 通过 | 490 ms | 合成对象上传、HEAD、下载和哈希校验通过 |
| 阿里云短信配置 | 部分通过 | <1 ms | 配置可读；真实发送未执行 |
| MinerU | 通过 | 363 ms | OSS PDF URL 成功提交并返回任务引用 |
| Chat 模型 | 通过 | 4,014 ms | 真实模型请求返回有效文本 |
| Vision 模型 | 通过 | 4,866 ms | 真实图像理解请求返回有效文本 |
| Embedding | 通过 | 405 ms | 返回 1,024 维向量 |
| Rerank | 通过 | 316 ms | 返回 3 条排序结果 |
| Realtime ASR | 通过 | 5,304 ms | WebSocket 建连并收到合成语音转录事件 |
| PostgreSQL | 通过 | <100 ms | 在生产容器环境连接成功 |
| pgvector | 通过 | <100 ms | 扩展存在且最近邻查询正确 |

本机 PostgreSQL 未启动，因此本地集成报告中的 PostgreSQL 和 pgvector 为失败；在生产容器环境补测后两项均通过。

## 5. 核心业务 E2E

安全 E2E 使用合成数据，整体耗时 23.307 秒，4 个场景全部通过。

### 5.1 账号与资料

- 合成账号注册和 Token 获取通过。
- 简历上传、处理和完成状态通过。
- JD 上传、处理和完成状态通过。
- 知识库上传、切分、Embedding、向量写入和完成状态通过。
- 资料与面试会话绑定通过。

### 5.2 RAG 面试回答

- 面试创建、资料确认和开始面试通过。
- 知识库检索命中 1 条最终片段。
- Chat 模型完成回答。
- 回答历史可查询。
- RAG 回答单次实测总耗时约 7.46 秒。

结论：功能已拉通，但未达到产品期望的 3 秒内输出完整回答目标。流式首字时间未在本轮 E2E 报告中单独记录，仍需补充线上性能观测。

### 5.3 截图回答

- 截图上传通过。
- Screenshot Prompt v2 生效。
- Vision 模型完成回答。
- 截图回答历史可查询。
- 截图回答单次实测模型及任务耗时约 3.46 秒。
- 最新修复已避免将 JSON 字段、转义符或包装内容直接展示给用户。

结论：后端链路已拉通，未完成真实浏览器视觉展示验收。

### 5.4 实时语音

- Realtime Speech 服务在线。
- Redis Runtime Store 生效。
- Protocol Version 为 2.0。
- Transport 为 WebSocket v2。
- 合成音频帧进入后端并产生转录/回答事件。
- 真实 Realtime ASR WebSocket 请求通过。

结论：后端 ingest、Redis、ASR 和事件发布链路可用；本机桌面真实采集端失败，因此用户真实声音到网页的完整链路未通过。

### 5.5 历史与结束面试

- 会话上下文可查询。
- 普通回答历史可查询。
- 截图回答历史可查询。
- 实时语音事件可查询。
- 结束面试通过。
- 会话列表在结束后仍可查询。

## 6. 线上服务

### 6.1 容器

| 服务 | 状态 |
| --- | --- |
| Web | Running |
| Backend | Healthy |
| PostgreSQL | Healthy |
| Redis | Healthy |

### 6.2 公网接口

| 地址 | 结果 |
| --- | --- |
| `/` | HTTP 200 |
| `/healthz` | HTTP 200 |
| `/api/v1/billing/status` | HTTP 200 |
| `/api/v1/auth/status` | HTTP 200 |
| `/api/v1/realtime-speech/status` | HTTP 200 |
| `/api/v1/screenshot-answer/status` | HTTP 200 |
| 未登录访问资料接口 | HTTP 401，符合权限预期 |

### 6.3 SPA 路由

`/login`、`/materials`、`/interviews`、`/billing`、`/guide`、`/download`、`/privacy` 和 `/terms` 均返回 HTTP 200，单次请求约 81–97 ms。

### 6.4 HTTPS 与安全响应头

- HTTPS 可访问。
- HSTS 已启用。
- CSP 已设置。
- `X-Content-Type-Options: nosniff` 已设置。
- `X-Frame-Options: DENY` 已设置。
- `Referrer-Policy` 已设置。

## 7. 桌面助手

### 7.1 构建与安装包

- macOS arm64 构建通过。
- 发布 ZIP 存在。
- ZIP 包含 1,520 个文件。
- ZIP SHA-256：`606c5db533309c0300c9f44b392ea2459b03d09eafb5098e8c908ef331d08fb3`
- App Bundle ID：`com.offersteady.companion`
- `codesign --verify --deep --strict` 通过。

### 7.2 商业发行状态

当前签名状态：

- `Signature=adhoc`
- `TeamIdentifier=not set`

该安装包只适合本地测试，不符合正式 macOS 商业分发要求。每次重新构建后，macOS 可能将其识别为新的应用身份，造成麦克风、录屏和系统音频权限失效。

### 7.3 真实采集诊断

| 检查 | 结果 | 错误 |
| --- | --- | --- |
| Native Runtime | 部分可用 | Screen Capture 未授权 |
| 麦克风权限 | 已授权 | 但默认输入设备格式不可用 |
| 麦克风帧 | 失败 | `microphone-device-not-found`，0 帧 |
| 系统音频/屏幕权限 | 失败 | `screen-capture-permission-required` |
| 系统音频帧 | 失败 | 0 帧 |
| 线上 Backend | 通过 | 可访问 |

诊断结论：`desktop-real-capture-no-frames`。

## 8. 数据持久化检查

生产环境已使用：

- PostgreSQL：账号、资料、知识库集合、面试会话、积分、账本、兑换码、商业化状态和向量。
- Redis：实时语音运行时状态。
- OSS：原始资料、处理产物和截图对象。

当前仍使用内存仓库：

- Chat Answer Task / History Repository
- Screenshot Answer Task Repository
- Screenshot Upload Runtime Repository
- Document Processing Task Repository

风险：后端容器重启后，正在进行或仅存在于内存中的回答任务、截图任务、上传运行态和处理任务状态可能丢失。即使资料、会话和向量仍在 PostgreSQL/OSS，页面也可能无法恢复完整的任务历史或处理中状态。

## 9. 阻塞缺陷与风险

### P0：正式发布阻塞

1. 桌面助手真实麦克风和系统音频均未产生帧，真实语音面试链路未通过。
2. 桌面安装包仅 ad-hoc 签名，权限身份不稳定，未进行 Developer ID 签名和 notarization。
3. Chat、Screenshot 和 Processing Task 仍有内存状态，后端重启后存在任务与历史丢失风险。

### P1：商业闭环阻塞

1. 未执行真实阿里云短信发送、验证码校验、同设备免登录和 Token 刷新 E2E。
2. 未执行真实码支付下单、付款、异步通知验签、幂等到账和重复回调 E2E。
3. 缺少浏览器级严格 UI 测试，无法证明线上页面点击流程完全没有 fixture/mock 泄漏。
4. RAG 普通回答实测约 7.46 秒，未达到 3 秒目标。

### P2：建议优化

1. Web 主 Chunk 约 780 KB，应按页面或能力拆包。
2. FastAPI 测试默认会读取真实 `.env`，存在误发短信、产生模型费用和测试不稳定风险。
3. Starlette TestClient 使用方式存在弃用警告，应升级测试适配。
4. 下载接口不支持 HEAD 请求，返回 HTTP 405；不影响 GET 下载，但不利于监控与 CDN 探测。

## 10. 未执行项

以下测试需要真实用户、设备、支付或浏览器环境配合，本轮未执行：

- 向真实手机号发送验证码并完成登录。
- 浏览器关闭后使用 Refresh Token 自动恢复登录。
- 真实支付一笔最小金额订单。
- 验证支付平台异步通知签名与权益幂等到账。
- 在网页中完成资料上传、创建面试、选择资料、实时回答和结束面试的人工点击验收。
- 使用当前真实机器码和面试 Session 完成桌面配对。
- 在耳机连接状态下验证麦克风自动切换、系统音频采集和双角色转录。
- 验证网页下载按钮实际下载并首次启动桌面 App。
- macOS Developer ID 签名、公证和 Gatekeeper 验收。

## 11. 发布建议

### 当前建议

可以用于：

- 开发人员自测
- 内部演示
- 少量受控 Beta 用户
- 不涉及真实付款的体验验证

暂不建议用于：

- 大规模公开发布
- 不受控真实付费
- 对实时双通道语音有稳定性承诺的商业用户
- 依赖容器重启后完整恢复所有回答与截图任务的场景

### 建议放行门槛

1. 修复桌面真实麦克风和系统音频采集并完成耳机场景 E2E。
2. 完成 Developer ID 签名与 notarization。
3. 将 Chat、Screenshot、Upload Runtime 和 Processing Task 持久化。
4. 完成一笔真实短信登录验收。
5. 完成一笔最小金额真实支付及回调幂等验收。
6. 增加并通过线上 Playwright 浏览器 Smoke Test。
7. 为普通回答记录首字时间、完整时间、RAG 各阶段耗时，并将首字体验控制在目标范围内。

## 12. 相关原始报告

- 第三方集成：`artifacts/integration-reports/ivr-0829ec6f4f1648bfa5d79ec0a00eedb8/report.md`
- 安全 E2E：`artifacts/integration-reports/e2e-55d0e779303c4b04badb41f9508c45ff/report.md`
- 桌面诊断：`artifacts/desktop-runtime-diagnostics/diagnostic-1784926849424.json`

