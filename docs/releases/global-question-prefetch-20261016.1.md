# 国际服问题预取优化发布 — 2026-10-16

**2026-10-16 01:04:52.674（Asia/Shanghai）已完成 Global Backend 上线，发布后独立复验通过。** 本次同步国服本轮问题预取合并、有限并发和资料安全缓存优化，减少连续转写引起的重复后台检索；详细本地结果见 [候选验收记录](global-question-prefetch-local-20261016.1.md)，需求及逐场景核对见 [OpenSpec 提案](../../openspec/changes/sync-global-question-prefetch/proposal.md)与[场景验证](../../openspec/changes/sync-global-question-prefetch/verification.md)。

## 已生效范围

只更新 Global Backend 的 Chat、Realtime 相关节点与新增预取调度器。首段及时准备，中间更新合并，final 优先；最多两个 worker、256 个键，缓存最多 128 个问题并在 60 秒后过期。缓存匹配当前身份、完整问题和资料版本；会话清理/reset/shutdown 撤销旧任务，用户点击回答保留原非等待启动和详细检索。

Global 原有独立会员/收费、七天及以上套餐准入、UTC 每日三场、无国服积分和 60 分钟截止的规则保持；语言、模型、全部 Prompt、TTS、Creem、heartbeat/ACK、普通/模拟隔离保持。模拟面试线上 `enabled` 原为 `false`，本次仍为 `false`。Web、Windows/macOS 助手及三平台 1.3.5 下载、Admin、worker、数据库/Redis、国服均未发布。未执行额外数据库迁移、数据清理或真实用户面试创建。

## 实际基线、候选和回退

| 项目 | 已核验值 |
| --- | --- |
| 切换前实际 Backend Image | `sha256:1dab56432de7606b172e30c84033e82fc44a236015c1e21a6ad0826e33be6348` |
| 本次 Backend Image | `sha256:b31a810a49f718e360f8ddbcbae0e7aa3d0184012b8993cd0e2f5f973bc7657a` |
| 本次 Backend 容器 | `c2b7caa35c86c85c13c4f9baeebb1da30465562d4ad50126c56db3d141d5bd4e` |
| 本次镜像标签 | `offersteady-global-backend:question-prefetch-20261016-1` |
| 固定回退镜像 | 上述实际旧 `1dab5643…` 镜像，未触发生产回退 |
| 回退镜像标签 | `offersteady-global-backend:question-prefetch-rollback-20261016-1` |
| 服务器私有发布目录 | `/opt/offersteady-global/releases/20261016-global-question-prefetch-1` |

发布前实际 app/Prompt 清单 235 个文件与重建源全部匹配，裸镜像与容器业务源码一致。候选只变化两个已有文件并新增调度器，其余 233 个既有文件保留；上线后为 162 个 app 文件和 74 个 Prompt。三个实际候选文件冻结 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `services/chat_service.py` | `46d9db278aadc4eae36f8a17552ee307e9ddcdbd386c8d3f4297f86b70b8f890` |
| `services/realtime_speech_service.py` | `d344c6089035fe5fd1a33a82425cc28637acf362447fb745ba5ab80e28594e69` |
| `services/question_prefetch_scheduler.py` | `36bc5ab7fc2329945a3becdedc0ccc0a38356c334e8b32a735610c58774d744f` |

170 个原方法、六个 caller 定点字节修改、其余顶层/类 AST、19 个模块路由与 74 个 Prompt 均通过保护核对。候选针对实际 Global 源构建，未整包重建或整文件覆盖共享研发源码。

## 验证和切换结果

- 实际 Global 源候选 **331 项测试通过**，另有 **16 项回答流程**与 **16 个 unittest subtests** 通过；发布控制器/门禁保护 **184 项通过**。本机专用合成 PostgreSQL/Redis 与固定 provider 验证，没有访问生产数据库或真实模型/音频供应商。共享宽测试的既有基线差异及测试专用适配保留在本地记录，不能表述为全仓全绿。
- 独立审阅核对全部源码边界，实际构造 Global 服务验证 observer、调度、token 撤销、reset/shutdown；确定性并发测试确认实际 reset 先释放 frame lock 再等待 stable 清理，没有发现锁环。初次缺失 helper 和独立健康核验缺口修复后重跑通过。
- 实际候选镜像在 `network none`、只读文件系统、`cap-drop ALL`、`no-new-privileges` 下通过探针：网络请求、数据库操作、文件写入、子进程、worker 启动均为零；未导入 `app.main`、进入应用生命周期或解析依赖。
- 候选探针及上线运行源码复验覆盖 **162 app、74 Prompt、151 条 HTTP 路径、两个 mock WebSocket、170 个受保护方法、19 个模块路由**；Global 权益、关闭开关及助手 1.3.5 保留。
- 冻结实际运行的 **四个 Compose、一个 Env 文件**，保持 project directory、原顺序及完整渲染配置，仅以私有 overlay 切换 Backend 到固定镜像 ID。完整环境、有效模型/config、HostConfig 和挂载保持；有效配置摘要前后均为 `fd56081071dcad5b9a6933d31fab72919c07a88f335fd688117531e5f565338d`。
- 预检及切换紧邻阶段重复五项只读活动门禁，普通/笔试/模拟、网页/桌面租约、音轨、回答/截图、资料任务、未知元数据与读取异常的所有受保护计数均为零，门禁退出码均为零。没有清理生产记录制造空闲。
- 仅 Backend 重建容器，其余 **六个容器 ID、Image、启动时间**不变，共享运行标签保持。Backend 地址无需代理重载，`proxyReloaded=[]`。
- 独立 `verify` 再次确认 healthy、restart 0、源码/配置/模型/路由和其它组件均通过。五个匿名公开 HTTP 检查均为 200：`/healthz`、`/login`、会员目录、模拟能力和网页构建标识；除含动态信息的 health 外，另外四项 body/data SHA 与发布前完全相同，模拟开关保持 false。
- 上线后截至 135 秒的短观察：服务 running/healthy、restart 0，其余六个组件身份再次核对不变；结构化 ERROR/CRITICAL、Traceback、HTTP 5xx 日志计数均为零。5xx 统计同时覆盖 Uvicorn access 行与结构化 `status_code`/`statusCode`/`httpStatus` 等字段，仅导出聚合，未导出用户原始日志。

## 运维证据和回退

[发布控制器](../../scripts/release_global_question_prefetch.py) SHA-256 为 `ca4cfc746b058bb5750b64dac6a76e22d520154f995a8bc9cd5a5181d659c0f6`，门禁与合成回归见[源码支持目录](../../scripts/release_support/global_question_prefetch_20261016/README.md)。控制器支持 `verify` 和 `rollback`；回退须重新核对输入/配置、当前容器属于本轮且没有后续发布、即时无受保护工作，仅恢复固定旧 Backend 镜像。故障恢复、后续发布归属、新活动和异常健康拒绝已通过合成回归，未在生产制造故障演练回退。

脱敏本地证据位于 `artifacts/global-question-prefetch-20261016/`：`production-preflight.json`、`production-deploy.jsonl`、`production-verify.jsonl`、`public-before.json`、`public-after.json`、`production-short-observation.json`；源保护、测试和独立审核位于其 `verification/`。完整配置、容器检查与凭据仅留服务器私有发布目录。

服务器后续操作必须读取实际容器镜像、Compose 文件顺序和本次私有 overlay。旧发布目录、`current`、共享标签及健康版本字符串不能替代组件实际基线，后续发布也不能直接使用混合 Git 源整包覆盖区域行为。

## 效果边界和用户验收

合成同负载检索 41→2、会话读取 41→3，final 资料就绪约 677→36.8ms，证明重复后台工作减少及最终问题准备得到保护；它不代表真实流量下整体 P95 已达到某个降幅。上线切换没有活跃面试，未执行真实面试、实体设备收音或真实模型主观效果验收，135 秒错误观察也不等于长期稳定性结论。

用户可从 [国际服登录](https://offersteady.com/login) 继续普通面试，重点检查连续提问字幕、点击回答及资料引用。后续结合真实流量下 API P95、错误率和面试响应速度验证实际收益。
