# 国服鉴权与状态读取优化：生产发布记录

2026-10-17 **01:05:53（北京时间）**，按用户授权完成国服 Backend 的鉴权与状态读取优化发布；随后独立 verify 和短时错误检查通过。用户现在可刷新[国服页面](https://mianshiwen.cn/login)测试，无需更新助手。

准备时曾发现一场普通面试、页面租约及桌面/音轨活动，门禁拒绝切换。用户确认属于真实用户并要求等待，随后按每五分钟检查继续执行。01:04 的检查确认面试已结束、五道保护检查通过，才进行发布；没有结束面试、清理记录或放宽门禁。“国服鉴权优化待空闲发布”自动检查已在发布与 verify 成功后停用（PAUSED），不会重复发布。

关联 [OpenSpec 发布规范](../../openspec/changes/lighten-cn-auth-and-state-reads/specs/cn-auth-state-protected-release/spec.md)、[任务](../../openspec/changes/lighten-cn-auth-and-state-reads/tasks.md)、[本地验收](cn-auth-state-local-20261016.md)、[发布控制器](../../scripts/release_cn_auth_state.py)和[发布支持](../../scripts/release_support/cn_auth_state_20261017/README.md)。10 月 16 日本地交付记录仍保留原日期和 local-only 事实。

## 内容和范围

只更新 CN Backend 的八个已验收文件：鉴权 port、AuthenticationService、内存/PostgreSQL 鉴权仓库、SessionService 及 session/web/realtime_speech 三个状态模块。常态鉴权由四个连接、三次读取及一次整行写入降为一次权威读取，last-used 以 60 秒间隔条件更新；idle 使用生命周期投影，列表资料只在同次调用复用，八个同步状态读取交由现有线程池执行。

逐请求鉴权、退出/撤销/封禁、资料下次请求新鲜度及原有错误合同保持。登录会话“最近使用时间”的精度约为一分钟。国服每日会员免费一场、其余 100 积分及开始后 60 分钟结束、普通面试计费、模型/Prompt、预取、心跳、ACK、Windows/macOS 助手 1.3.5 及功能开关保持；不更新国际服、Web、Admin、worker 或数据库服务，不新增迁移、配置项或依赖。

## 实际基线和候选

| 项目 | 值 |
| --- | --- |
| 原实际 Backend 镜像 | `sha256:cc040a55f261a37226272c31937744e6ca4bd7a8c25e0810e360d218d41acfc0` |
| 原实际 Backend 容器 | `7e3ea04495bcaec9d8c072b892dcd86a87735af4ada2f002aaef92eae1039d25` |
| 本轮已发布 Backend 镜像 | `sha256:4c305868ca6799cb7b8a69afd691f2e2e966785dfce827a0e04c51fa431fd656` |
| 本轮实际 Backend 容器 | `d511cdfbb9680034eefeeb2a61435af8c217100b43c6cab25ed150841893e895` |
| 新镜像标签 | `offersteady-cn-backend:auth-state-20261017-1` |
| 原镜像回退标签 | `offersteady-cn-backend:auth-state-rollback-20261017-1` |
| 服务器私有发布目录 | `/opt/offersteady/releases/20261017-cn-auth-state-1` |
| 本轮目标 overlay | `compose.auth-state.json`，只设置 Backend 固定 Image ID |
| 发布控制器 SHA-256 | `1973076ddd11befe0a6a1dbe93daebd51b09a56b114ad92e9fa081765900982b` |

发布前实际运行的 168 个 app/Prompt 文件与已验收基线逐一核对完全一致，原容器 healthy、重启计数 0。裸镜像与可写层源码也一致。候选以该实际镜像为基础仅 COPY 八个验收文件，原镜像配置和 RootFS 层前缀保持；另外 160 个文件和 210 个未批准方法保持。未从包含其它区域研发内容的组合工作区整包构建。

模型/环境、完整渲染 Compose、所有实际 Compose 文件顺序/项目目录、HostConfig、挂载、七个非目标容器及共享 `compose-backend` 标签映射已冻结。私有环境、容器完整配置和异常详情只留服务器，不导出凭据。

## 发布验证和保护

- 复用本地已验收候选：433 项相关测试通过，另 16 个 subtest，一项 Global 专有场景跳过；13 项原基线也存在的共享测试差异明确记录，未宣称全仓全绿。
- 本轮发布控制器、活动门禁和 probe 共 **227 项合成测试通过**，并经独立审查；不包含真实用户或供应商调用。
- 实际候选镜像通过 `network none`、只读文件系统、cap-drop/no-new-privileges 的探针，验证 148 个 app 文件（含一个历史资源旁文件）、20 个 Prompt、210 个保护节点、八个同步入口、合成 JWT/撤销/touch 以及原收费和预取边界。没有进入应用生命周期、数据库或供应商。
- 离线 api_router shell 为 140 条业务路径、两条模拟 WebSocket；实际运行服务还包含 Admin、推广及健康入口，共 **195 条 HTTP 路径**。两类清单分开保护，不把 shell 清单当成完整运行路由。
- 离线 schema SHA：`87d07432b35c17df7c71411c73725e7d11e22b3b2f83032b4a71393f3cb5def1`。实际完整 schema SHA：`6b256080db7d4d0d5eefd6ad088ab0efc69684dc7b3ea9d71da5221645ccc0f4`；发布前后均要求完整路径/方法和 schema 相等。
- 切换及回退必须执行原有五道只读门禁，覆盖普通/笔试/模拟、准备、租约、桌面/音轨、回答/截图及资料工作。保留仅七条超过 24 小时且 durable job 已失败的旧 QUEUED 资料任务例外，不改变判定条件或用户记录。
- 自动恢复的门禁在冻结基线镜像、原环境与原网络的独立只读容器中执行，不依赖故障候选可 exec；仍拒绝新活动、归属漂移或不可权威读取的状态。未触发真实生产回退演练。

## 切换结果与复核

- `preflight` 通过后，`deploy` 临切前连续执行两轮五道活动门禁并重新核对当前镜像、配置与全源身份；所有受保护活动为零。历史 completed 模拟面试 32 条及七条既有旧失败任务例外保留，不修改用户数据。门禁是检查时点判断，不是原子预约或绝对无中断保证。
- 仅用私有固定镜像 overlay 对 Backend 执行 `--no-build --no-deps --pull never` 更新。Backend IP 保持，不需要重载代理。其它七个容器的 ID、Image 和启动时间逐项保持，未更新共享镜像标签或源码指针。
- 发布后和单独 `verify` 均确认实际镜像/容器归属正确、healthy、重启数 0；完整 168 文件、210 保护节点、20 Prompt、八个同步入口、195 条实际 HTTP 路径和完整 OpenAPI SHA 通过。
- 模型/有效配置、全部环境变量、完整 HostConfig/挂载及原 Compose 文件保持；公网 `/healthz` 与 `/login` 返回 200，原收费、预取、心跳、ACK 和助手清单保护通过。
- 新容器启动后 **166.24 秒**的只读日志摘要：结构化 ERROR、CRITICAL、Traceback 及已解析 HTTP 5xx 均为 0；观察结束时仍 healthy、重启数 0，七个非目标容器仍保持。未导出原始用户日志。
- 未触发生产回退；失败恢复的活动与归属保护仅通过本轮合成测试和独立代码审查，不宣称生产回退演练已执行。

脱敏证据在本地 `artifacts/cn-auth-state-20261017-release/` 的 `production-deploy.json`、`production-verify.json`、`production-observation.json` 和 `production-spec-verification.json`；此前本地测试和源码冻结证据仍在 `artifacts/cn-auth-state-20261016/`。完整私有环境和诊断仅留服务器发布目录。

## 运维

服务器只读复核命令：

```bash
python3 -B /opt/offersteady/releases/20261017-cn-auth-state-1/release_cn_auth_state.py verify
```

如后续需要回退，仅使用同一控制器的 `rollback` 动作。它会重新核对本次发布归属、固定原镜像、完整配置和活动门禁；出现其它发布或新保护活动时拒绝覆盖。不可通过旧共享标签、旧目录整包或重启其它组件进行回退。

## 验收边界

本轮已完成实际部署、完整性及短时健康验收；短时日志无错误不能证明持续真实流量 P95 已改善。真实流量 P95、物理收音和用户面试体验仍由后续测试验证。本轮验证未创建真实面试、调用真实模型、生产压测、独立执行数据库迁移或提交/推送 Git。
