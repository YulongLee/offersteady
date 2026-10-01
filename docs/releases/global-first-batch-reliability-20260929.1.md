# 国际服第一批可靠性修复 — 2026-09-29

## 发布结果

- 已发布：`20260929-global-reliability-1`，基线为国际服实际运行的 `20260922-global-telemetry-p0-1`。
- 约北京时间 04:25 切换，仅重建 Global Backend / Web；国服未操作。
- 最后空闲门禁时间戳 `1790627085766`：live 面试、近 5 分钟准备、有效 live 页面租约、近 30 秒音频和未完成回答任务均为 0。
- Backend 健康，Backend/Web 重启计数为 0；首页、登录、应用和管理站点可访问。
- 其他容器 ID 未变，全部容器环境变量哈希保持原样；没有数据库迁移。

## 本轮范围

1. 回答启动：在发送 SSE 响应头前处理权益拒绝，预留失败结果只返回支持字段，避免额外字段引发 TypeError。
2. 截图失败：补齐异常日志必需参数，保留原始异常与恢复异常的类型，不记录图片或原始敏感内容。
3. 简单回答：新增向后兼容的 `quick-completed` 事件与默认字段。简单阶段立即独立完成；详细阶段失败、取消或流中断时保留已收到的简单内容，并退出加载状态。
4. 国际服 macOS Intel：正式发布 1.3.2，补齐签名、公证与下载清单。Apple Silicon / Windows 的既有产物与清单字段不变。

未同步模拟面试、联网回答、国服积分规则或管理页；未变更模型、Prompt、音频、轮询和内存策略。Global 邮箱认证、多语言、Creem 及权益规则保持现有实现。

## 验证

| 检查 | 结果 |
| --- | --- |
| 回答/截图专项后端测试 | 23 通过；同一测试在未修改 Global 基线上为 12 失败 / 11 通过，可复现缺陷 |
| Global 认证、权益、多语言、回答等后端回归 | 113 通过 |
| 新增 Global 简单阶段 UI/流测试 | 8 通过，含桌面/窄屏与详细失败场景 |
| Global 前端全量测试 | 103 通过、3 失败；3 项在未修改基线上同样失败，见下文 |
| 排除上述 3 项旧断言后 | 103 通过、3 跳过 |
| Global 文案审核、类型检查、生产构建 | 通过；637 条文案审核通过 |
| 无网络实际候选镜像测试 | 新旧任务解码、启动拒绝、事件顺序、10 种语言及 Global 认证/支付路由通过 |
| 回退镜像兼容测试 | 可读取新增 `quick_answer_completed` 字段 |
| Nginx 配置 | 通过 |
| OpenSpec 严格校验 | 通过 |

未修改基线上已存在的 3 项前端断言失败：

- `HomepageFeedback`: exposes the same quotes in static HTML without review schema。
- `global-product`: places translated anonymous feedback between benefits and pricing。
- `public-commercial-disclosures`: retains the authoritative v2 catalogue and separates billing types。

以上为首页评价和历史支付文案断言，未纳入本轮修改，不能宣称整个仓库测试全部通过。测试使用合成数据，未在生产创建用户、面试、订单或调用付费模型。Intel 安装包验证覆盖架构、签名、公证和下载，未代替真实 Intel 设备上的收音体验验收。

## 线上核验

- 已部署 7 个后端覆盖文件的哈希均匹配候选版本。
- Global 配置、语言注册表、依赖选择、认证、支付和权益实现哈希与原镜像一致。
- 套餐目录共 5 项，前后规范化内容 SHA256 均为 `3c082fd29ec1f9ea523ee56351f75d02ceb13845f9c9afb6ae99dcefbc41b924`。
- Creem 保持 live / enabled / ready，阻塞项为空；未创建支付交易。
- 前端构建标识确认 Global / Creem / `20260929-global-reliability-1`。
- 线上 `main-SHx6gMHK.js` 和 `AnswerWorkspace-ipgDk8kn.js` 与本地构建逐字节一致。
- Windows x64、macOS arm64/x64 下载入口均为 1.3.2，Range 请求返回 206，完整长度匹配清单。
- 切换后首次日志核验：Traceback 0、ERROR 级别 0；这仅是上线窗口观察，不是长期零故障保证。

## Intel 安装包

- 文件：`OfferSteady-Companion-Global-1.3.2-macOS-x64.dmg`。
- 大小：143346577 bytes。
- SHA256：`01fa7d6217d90f7dcea6264f37292a73dfbf41dd02da288b4b04e2b09a490b9f`。
- App 公证 Accepted：`82a0a5b2-d5b2-497e-a3e0-966ab86f7c77`。
- DMG 公证 Accepted：`87d44de4-5091-4221-9534-de48a69d686f`。
- App / DMG 已装订公证票据，签名、Gatekeeper、公证票据校验通过。
- 全球端点、bundle ID、x86_64 架构、1.3.2 应用版本已核对；不含未发布的模拟面试桌面改动。
- 正式对象：`global-desktop-releases/macos/x64/1.3.2/OfferSteady-Companion-Global-1.3.2-macOS-x64.dmg`。
- 发布脚本最初从旧 package.json 读到 1.3.0，修正元数据后重新发布到上述正确路径。曾生成一个未被最终清单引用的临时对象：`global-desktop-releases/macos/x64/1.3.0/OfferSteady-Companion-Global-1.3.2-macOS-x64.dmg`；没有覆盖既有 1.3.0 文件，未做广泛 OSS 删除。

## 镜像与回退

| 用途 | 镜像 |
| --- | --- |
| 新 Backend | `offersteady-global-backend:reliability-20260929-1`，`sha256:e703d5b4b0db8759cd568a817c18de9eca3e2b9c1f4bce1a82663464391d602c` |
| 新 Web | `offersteady-global-web:reliability-20260929-1`，`sha256:8d34b4e2068d9da6834d0754ece1809b965f2b90a1b504aaa4d46f67c76a15ef` |
| 兼容 Backend 回退 | `offersteady-global-backend:reliability-rollback-20260929-1` |
| Web 回退 | `offersteady-global-web:baseline-20260929`，原镜像 `sha256:e4b6526e4b21e8b24030dfb31de2ada122d58b3b9b701f6d36cb01cf804a48c8` |

服务器当前发布目录：`/opt/offersteady-global/releases/20260929-global-reliability-1`。环境文件从旧发布原样复制，因此 Backend 环境内的旧 APP_VERSION 标签保留；精确发布身份以镜像、当前目录和 Web 构建标识为准。

回退须再确认无在线面试，使用兼容镜像而非直接切回完全不认识新增字段的旧 Backend：

```sh
cd /opt/offersteady-global/releases/20260929-global-reliability-1
docker exec -i -w /app/apps/backend offersteady-global-backend-1 python - < deploy/check-idle.py
# 仅上一条成功（所有计数为 0）后执行：
docker compose -p offersteady-global --env-file .env.global.production \
  -f infra/compose/docker-compose.global.yml -f deploy/compose.rollback.yml \
  up -d --no-build --no-deps backend web
```

回退后核查健康并记录回退状态，不清除 Redis 用户任务，也不重建其他服务。当前未执行回退。

## 本地证据

隔离源代码、日志和已公证产物保留在 `artifacts/global-first-batch-20260929/`。该目录包含无凭证的 `baseline/`、`candidate/`、部署脚本和测试日志。工作区原有国服改动未被覆盖；本轮没有执行 Git 提交或推送。
