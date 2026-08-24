# 商业化实时转写发布与隔离 Beta

## 用户可见行为

- 麦克风和电脑输出保持两个独立声道，每个声道只有一个活动草稿。
- 已确认或“识别未完成”的片段都是终态，迟到的局部转写不能把它恢复成“转写中”。
- 普通静音、持续底噪和最长说话时间都会得到有界的终止结果。
- 后端超过 watchdog 边界仍未获得可靠结束时，只结束并重建异常声道；另一声道继续工作。
- “识别未完成”仅保存最后一份稳定文本供用户参考，不会自动回答、不会扣回答积分。
- 只有用户点击快答、截屏回答或提交手动问题才会创建回答任务。

原始音频仍只存在于桌面端与后端的有界内存队列中，不写入 PostgreSQL、Redis、OSS、日志或性能报告。

## 终止协议

新客户端可携带以下可选字段，旧客户端在兼容窗口内仍可使用：

- `turnState`: `idle | speaking | tail | committing | final | incomplete`
- `finalizationReason`: 静音、硬期限、停止、watchdog 等不含内容的原因码
- `sourceGeneration`: 声道连接代次，用于拒绝旧连接的迟到事件
- `terminalId`: 终止帧幂等标识

终止帧是控制面工作。队列满时可以合并或替换过期局部帧，但不能驱逐已排队的终止帧。客户端在未收到 `terminal-accepted` 前保留并重发相同终止意图。

## 功能开关与回滚

- 桌面：`OFFERSTEADY_REALTIME_ENDPOINTING_MODE=commercial-adaptive|legacy-threshold`
- 后端：`OFFERSTEADY_REALTIME_SOURCE_WATCHDOG_ENABLED=true|false`
- 后端：`OFFERSTEADY_REALTIME_TERMINAL_ACK_ENABLED=true|false`

回滚顺序是先关闭单个新增行为，而不是回滚整个产品：终止确认、watchdog、桌面自适应 endpointing 可独立关闭。运行中的面试不应在中途切换桌面传输协议。

## 隔离 Beta

Beta 使用 Compose 项目 `offersteady-beta`、独立 PostgreSQL/Redis 数据卷和仅绑定本机回环地址的端口：

- Web: `127.0.0.1:18080`
- API: `127.0.0.1:18000`
- PostgreSQL: `127.0.0.1:15432`
- Redis: `127.0.0.1:16379`

配置步骤：

1. 从 `.env.beta.example` 创建未纳入 Git 的 `.env.beta`，只使用合成测试账号与 Beta 存储命名空间。
2. 运行 `BETA_ENV_FILE=.env.beta ./scripts/beta-realtime-guard.sh`。
3. 运行 `BETA_ENV_FILE=.env.beta ./scripts/deploy-realtime-beta.sh`。
4. 将 `infra/caddy/Caddyfile.beta` 合并到受控的 Caddy 配置，并让 `beta.mianshiwen.cn` 只反代上述回环端口。
5. 运行 `./scripts/check-realtime-beta-non-regression.sh`，同时确认正式域名与生产容器未改变。
6. 测试结束运行 `./scripts/teardown-realtime-beta.sh`。该脚本默认保留 Beta 数据卷，便于复盘。

Beta 禁用真实支付、副作用型短信与生产桌面发布清单。禁止复制生产用户、面试、材料、转录、支付或积分数据。

## 故障排查

### 长时间显示“转写中”

检查单个声道的 `terminalAgeMs`、`terminalAdmissionFailures`、`incompleteRecoveries`、`sourceReconnects` 和队列深度。若 watchdog 产生 `incomplete`，继续核查桌面终止帧确认和 ASR provider completion，而不是重启整场面试。

### 终止后再次出现局部文本

核对 `segmentId`、`revision`、`sourceGeneration`。Web 必须按终态优先级丢弃迟到 partial；后端必须拒绝已退休 generation 的事件。

### 一条声道异常影响另一条

这是回归问题。恢复操作必须调用声道级 `close_source`，不能关闭整个 session。立即关闭 watchdog 新行为并保留诊断计数。

### Beta 影响正式服务资源

立即执行 Beta teardown；不得运行任何生产 Compose 重启命令。只有生产 API P95、CPU、内存、Redis 和数据库健康恢复后才能继续验收。

## 当前测量结果与限制

2026-08-24 本地 synthetic 候选结果：

- WebSocket acknowledgement 平均 `0.77 ms`，P95 `1.34 ms`
- 队列深度 `0`，无局部帧丢弃，终止片段均生成
- synthetic stop-to-terminal 为 `0 ms`
- 聚合快照在并发 10 的合成测试中将请求数降低 `75%`，P95/P99 均为 `15.72 ms`，错误数 `0`

这些数字验证本地控制面和状态机，不代表公网、真实 DashScope、用户声卡或会议平台耗时。真实可见首字、stop-to-terminal、前端渲染、CPU、Redis 命令量与 30 分钟双声道稳定性仍需要生产受控验收补充。

### 2026-08-24 资源受限直接灰度决策

当前生产服务器约 3.5 GB 内存，不具备长期并行运行第二套 Web、Backend、PostgreSQL 和 Redis 的安全余量。用户明确选择停止隔离 Beta，先执行本地完整验证，再进行兼容优先的生产灰度：

1. 保留生产回滚提交、镜像和 `0.1.16` 下载清单。
2. 后端 Watchdog 默认关闭，先部署兼容后端，再部署 Web。
3. 旧版伴随助手验证通过后才发布 `0.1.17` 的 macOS 下载清单。
4. Windows 因缺少 Authenticode 身份继续保留 `0.1.16`，不发布新的未签名安装包。
5. 任一健康、延迟或实时链路指标异常，立即恢复上一套镜像或下载清单。

发布前生产回滚基线：仓库 `7749258e7318242ab38d5bde8ceef47ff0096a8c`；Backend 镜像 `sha256:b36e53717e556e9eb76c9bc38d96ad5c061a22d5b9e0458eebfe4aa3d186c50e`；Web 镜像 `sha256:f6e785ecff645e8753ddbbdbf4e21e53f2d8eade412b73e3097dcdcfe93e113a`；Admin 镜像 `sha256:9d3b226cf6c30dfed8a06e13891d1a469ae63f2a574f74da4109a27e0cc178e7`。发布前健康检查 `200 / 61 ms`，可用内存约 `2293 MB`。

本轮本地完整测试结果：Backend `292 passed / 14 skipped`；Admin `34`、API `90`、Desktop `80`、Web `282`、Protocol `31` 全部通过；类型检查、正式 Web/Desktop 构建和 OpenSpec strict 校验通过。合成控制面确认 P95 `0.64 ms`、队列深度 `0`、终态丢失 `0`；10 并发聚合恢复 P95 `12.37 ms`，请求数相对旧四接口恢复降低 `75%`。

### 2026-08-24 正式 macOS 0.1.17 产物

| 架构 | SHA-256 | 签名与验证 |
| --- | --- | --- |
| macOS arm64 | `6cbe9fd5a5bc3c7b35155a0cbbd8d7973b4f5d83fdf72d9b40e9c02e13c5b4e2` | Developer ID、App/DMG Notarization Accepted、stapler、Gatekeeper、16 个 Mach-O 组件验证通过 |
| macOS x64 | `a21ab0c0ed946acc90c2e4b6a26f8dd9af2b4938fce196c9e5c0180341a40cda` | Developer ID、App/DMG Notarization Accepted、stapler、Gatekeeper、16 个 Mach-O 组件验证通过 |

### 2026-08-24 Beta 助手产物

| 架构 | 版本 | 本地 DMG | SHA-256 | 验证 |
| --- | --- | --- | --- | --- |
| macOS arm64 | 0.1.16 Beta | `apps/desktop/release/macos-beta/OfferSteady-Companion-Beta-0.1.16-macOS-arm64.dmg` | `c5dffaddae9f9fd1b056d48995300866b106d8e8d87a2d651ec0a295073d3497` | Developer ID、App/DMG Notarization Accepted、stapler、Gatekeeper 均通过 |
| macOS x64 | 0.1.16 Beta | `apps/desktop/release/macos-beta/OfferSteady-Companion-Beta-0.1.16-macOS-x64.dmg` | `f2ed8945e7eee5cc0fe10d90d60509e71e7d50d5d7287e292a04ba091d15a6fb` | Developer ID、App/DMG Notarization Accepted、stapler、Gatekeeper 均通过 |

Beta 清单位于 `apps/desktop/release/macos-beta/manifest.beta.json`，显式标记 `productionManifestEligible: false`。这些构建输出被 Git 忽略，不会进入正式官网发布清单。

`beta.mianshiwen.cn` DNS 已配置，但隔离 Beta 容器和数据卷已按资源决策停止并移除；没有为 Beta 切换 Caddy 路由。Windows 尚未提供 Authenticode 签名身份，不能使用 Apple 证书代替。

## 兼容与升级

- 后端和 Web 先保持对当前生产伴随程序的兼容；旧客户端缺少的新字段按可选字段处理。
- 完整的本地 endpointing 由 `0.1.17` 正式 Mac 伴随程序承载，并在服务端兼容性检查后进行受控用户验收。
- Beta 与正式伴随程序必须使用不同名称、应用身份、API origin 和更新清单，允许并存且不互相覆盖权限。
- 用户已明确批准资源受限的直接灰度；仍按“后端 → Web → 正式伴随程序清单”推广同一测试提交和不可变产物。
