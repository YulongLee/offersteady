## 1. Scope and baseline

- [x] 1.1 确认用户只授权本地优化开发/自测，晚上上线另行决定；锁定鉴权与状态读取范围及非目标。
- [x] 1.2 记录当前工作区与实际 CN 运行镜像/源证据基线，列明批准修改节点与既有预取、心跳、ACK、收费和区域差异保护项。`artifacts/cn-auth-state-20261016/baseline-binding.json` 核对实际 `cc040a55…` 的 168 个 app/Prompt 文件哈希；八个目标 working-before 与 HEAD 冻结一致，无线上变更。
- [x] 1.3 主代理阅读 apply 指令及全部 context，核对本次 Specs 的全部场景与实际实施计划，没有未经确认的产品行为变化；实现仍仅限本地。

## 2. Authoritative authentication

- [x] 2.1 实现内存和 PostgreSQL 请求内权威鉴权读取；PostgreSQL 常态一个连接、一个 SELECT 取得会话与用户可用性，去掉未消费的完整用户/身份加载。
- [x] 2.2 将 last-used 更新改为 60 秒限频的条件式元数据更新，无 UPSERT/整行覆盖；会话到期持久化也保护并发刷新/撤销状态。
- [x] 2.3 为缺失/坏签名/到期/撤销/封禁/用户缺失及 CN/Global 账户生命周期增加合成回归，证明每次权威校验且不新增绑定准入条件。
- [x] 2.4 在隔离 PostgreSQL 验证合法请求连接/SELECT/实际写行计数、并发 touch 至多一次，以及撤销/删除/过期/刷新/改密竞争不复活或覆盖。`auth-combined.xml` 72 项和 `auth-postgres.xml` 19 项通过；CN 候选鉴权 52 项通过，1 项仅 Global 生命周期跳过（已在工作区通过）。

## 3. Fresh state read paths

- [x] 3.1 将 idle_status 改为既有五字段生命周期投影，保留 owner、404/403、idle 边界、结束/结算/资源释放等原副作用与响应。
- [x] 3.2 为 list_sessions 的资料刷新增加本次调用局部 document ID memo，保留各会话归属/绑定校验，无跨请求/跨 owner 缓存。
- [x] 3.3 将八个纯同步状态 GET 入口交给现有 FastAPI/AnyIO 线程池执行，保留函数正文和所有公开合同，不修改独立控制执行器。
- [x] 3.4 增加 idle 投影零资料读取、资料请求内去重/下请求变更/owner 隔离，以及事件循环 sentinel、错误/后续请求恢复和 API 合同测试。状态专项与既有回归 72+36 项通过；工作区独立复核鉴权/状态 74 项通过。最终 CN 候选集验证仍归 4.1/4.2。

## 4. Local verification and delivery

- [x] 4.1 运行鉴权/状态新增专项、隔离 PostgreSQL 与现有 CN/Global 登录/刷新/改密/退出回归，记录准确命令和真实结果。工作区鉴权 53+Global 19 项、状态 40 项通过；实际 CN 源候选鉴权 52 项通过（1 项 Global-only 跳过），修正依赖名称兼容的新状态夹具在工作区/候选各 40 项通过，59 个断言 AST 全保留。既有 WeChat 生产拒绝断言在原/候选均同样失败，独立记录，未冒称全套绿。
- [x] 4.2 运行既有心跳、ACK、控制面、预取、会话清理、商业权益和区域隔离相关回归，确认无非批准行为退回。`candidate-regressions.json` 的限定候选集 381 项 pytest 加 16 项 unittest subtests 通过；13 项工作区/实际基线差异逐项在原镜像源码复现并显式排除。同毫秒排序旧边界在原/候选固定时钟下同样失败，单调合成时钟下 9 项状态合同两侧均通过；未修改运行排序或原断言，不代表所有仓库测试通过。
- [x] 4.3 使用相同合成数据对照原路径/候选，报告样本、并发、连接/查询/写行/资料读取数、P50/P95/P99 与失败数；标注本地收益边界。`benchmark-auth.json` 含 8×100 次本地 PostgreSQL 调用、零失败；状态原/候选各 4×64 次合成服务调用、零失败，均不包含执行池队列等待，不代表真实线上 P95。
- [x] 4.4 对实际 CN 镜像源码制作本地最小候选并验证全源差异、路由/方法、模块、Prompt 和未批准节点。`candidate-proof.json` 核对 168 个绑定文件恰 8 个批准文件变动、210 个未批准方法保留；`routing-proof.json` 证明 140 HTTP 路径、2 模拟面试 WebSocket、完整 OpenAPI 哈希、20 Prompt 和 19 模块保持。此为本地源候选保护，不是生产切换或容器运行验收。
- [x] 4.5 更新[本地验收记录](../../../docs/releases/cn-auth-state-local-20261016.md)，独立矩阵逐项核对 24 个 Spec 场景；七份文档十一个本地链接、`git diff --check` 和 `openspec validate lighten-cn-auth-and-state-reads --strict` 通过。最终源与测试 SHA 保存于 `artifacts/cn-auth-state-20261016/verification/final-verification.json`。
- [x] 4.6 交付本地改动、测试结果和限制：新增 93 项专项通过；实际 CN 候选合计 433 项通过、另 16 个 subtest、一项 Global 专有跳过，原有失败/排除及合成耗时边界均记录。无线上部署/重启/配置数据库变更、真实面试、生产压测或 Git 提交/推送；晚上上线另行授权并重新核对运行基线。

## 5. CN production release authorized on 2026-10-17

本节是 2026-10-17 用户新增上线授权后的生产阶段；1–4 节保留 2026-10-16 本地阶段的原事实与证据，不把旧 local-only 记录重写为已上线。

- [x] 5.1 确认新授权将已验收优化部署到国服，仅批准 CN Backend 八文件最小节点；追加 [生产发布规范](specs/cn-auth-state-protected-release/spec.md)，明确国际服/其它组件、收费/模型/Prompt/配置、Git 仍不扩大范围，且无需重复确认相同上线授权。
- [x] 5.2 发布前重新读取实际 CN Backend Image/容器、可写层和完整 app/Prompt/路由/OpenAPI、有效模型/配置、Compose 顺序/项目目录、环境/HostConfig/挂载与非目标组件身份；实际仍为 `cc040a55…` / `7e3ea044…`，168 文件与冻结基线一致、195 条运行 HTTP 路径/完整 schema 已绑定，7 个非目标容器及完整私有配置冻结。证据 `artifacts/cn-auth-state-20261017-release/runtime-before.json`、`live-routes-before.json`、`prepared-summary.json`。
- [x] 5.3 冻结仅八文件批准节点的生产载荷、全源/未批准节点和既有预取/心跳/ACK/收费/助手保护证明；候选镜像 `sha256:4c305868ca6799cb7b8a69afd691f2e2e966785dfce827a0e04c51fa431fd656` 已从实际原镜像增量构建并通过 `network none`、只读离线 probe，168 文件/210 未批准节点、20 Prompt、8 同步入口及合成鉴权通过，未切换线上。原镜像和有效部署配置仅保存在服务器私有发布目录。
- [x] 5.4 发布控制器和支持集合 227 项合成测试通过，独立终审无未解决 P1/P2；修复恢复门禁依赖故障容器问题，改为冻结基线/环境/网络的独立只读门禁；区分 140 条离线业务 shell 路径与 195 条实际完整 HTTP 路径。控制器 SHA `1973076ddd11befe0a6a1dbe93daebd51b09a56b114ad92e9fa081765900982b`，证据 `release-safety-tests.xml`。
- [x] 5.5 切换前连续复核权威活动门禁及当前部署/候选身份；早前两次真实 preflight 因 1 场 live 面试而阻断，后续切换记录中的两轮各五项门禁均通过，受保护活动/未知/失败计数均为零。32 场历史 completed 模拟面试和 7 条既有失败陈旧排队任务例外单列，未作为活跃工作；证据 `artifacts/cn-auth-state-20261017-release/production-deploy.json`、`preflight-attempt-1.json`、`preflight-attempt-2.json`。
- [x] 5.6 北京时间 2026-10-17 01:05:53 的真实部署记录确认仅 CN Backend 切换到固定镜像 `4c305868…`、新容器 `d511cdfb…`，exit 0、deployed true；环境/有效配置/模型、其它 7 个容器和共享运行标签保持，未重载代理。八文件载荷哈希与已验收候选匹配，独立证据矩阵见 `artifacts/cn-auth-state-20261017-release/production-spec-verification.json`；最终只读复核和短时日志仍待 5.7。
- [x] 5.7 最终 `production-verify.json` exit 0，实际镜像/容器与部署一致、healthy/重启 0，148 app/20 Prompt、195 完整 HTTP 路径/schema、模型/环境/有效配置和 7 个非目标容器保持；冻结控制器 `verify_live` 的成功返回要求匿名 `/healthz` 和 `/login` 均为 200。`production-observation.json` 的 166.24 秒短时观察 ERROR/CRITICAL/traceback/解析 HTTP 5xx 均 0；回退分支仅合成测试通过，未触发真实生产回退。`release-status.json` 为 deployed_verified，等待空闲的 heartbeat 已置 PAUSED，不把短时验收当作真实 P95 或物理客户端改善证明。
- [x] 5.8 更新[实际发布记录](../../../docs/releases/cn-auth-state-20261017.1.md)与 `release-status.json`（deployed_verified），九个发布场景均有真实或合成证据并区分未触发生产分支；166.24 秒日志观察无 ERROR/CRITICAL/traceback/已解析 HTTP 5xx，服务持续 healthy、重启 0，自动检查已 PAUSED。检查本变更及发布文档链接、diff 和 strict 通过；真实 P95/物理客户端效果仍待用户验收，保留旧本地证据，不执行 Git 提交/推送。
