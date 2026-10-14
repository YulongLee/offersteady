# 国服轻量心跳回归恢复（2026-10-15）

## 范围与当前阶段

用户授权：开发、本地自测通过后推送 Git 并部署国服，随后由用户真实设备测试。本轮只恢复轻量页面心跳，不调整字幕预取、轮询、模型、计费或其它产品行为。

已于 **2026-10-15 00:13:19（Asia/Shanghai）** 部署，仅切换 Backend；本地验证、Git 推送和候选验证均先于切换。发布准备目录沿用开始工作时的日期：`/opt/offersteady/releases/20261014-cn-heartbeat-restore-1`。这不是一个全栈源码替换目录。

## 实际运行基线与最小补丁

- 当前 Backend 基线：`sha256:567ddaf392216bad2b23644cf94f65b8b4c0b5f9cb982e6ae15be8891cac06e1`（笔试会员版本）。
- 修改前 `realtime_speech_service.py` SHA-256：`0f0b280f284b35625fc75d7615c1c2f43bf731f68230928ef6881c1fd86875a7`。
- 修改后 SHA-256：`fdef7f2f7cfb47302415dac9ba255e4be9cd4bdb928b04f1c92283ff487c0fc2`。
- 唯一变更节点：`RealtimeSpeechService.record_web_session_heartbeat`。已从运行容器导出源码验证：替回原方法后，完整模块 AST 等于基线。
- 正常心跳使用已有五字段权威投影；不读完整会话/绑定资料，不写会话/计费。鉴权、结束、空闲过期清理、页面租约和接管规则沿用已批准设计。
- [生产基线补丁](../../infra/releases/cn-heartbeat-restore-20261014.1.patch)、[恢复发布工具](../../scripts/restore_cn_web_heartbeat.py)、[隔离探针](../../scripts/probe_cn_web_heartbeat_restore.py)。

候选以当前实际镜像为基础仅增加一个 COPY 层。没有回滚到 10 月 10 日整镜像；当前笔试会员、模拟面试和所有非心跳方法均保留。Web 保持恢复后的 `pricing-copy-hourly-20261011.1` 镜像，状态去重仍未重新上线。

## 本地验证及已知边界

1. 在未修改的运行源码上，准备/进行状态的两项“禁止完整读取”测试均失败，成功复现本轮缺陷；替换单方法后心跳专项 27 项通过，包含真实本地 PostgreSQL 投影检查。
2. 在实际源码候选上运行心跳、空闲生命周期、计费、控制、资源回收、模拟面试 API/Postgres/准备/隔离、截图与探针回归：**196 passed / 4 deselected / 0 skipped**，16.08 秒。普通笔试会员与积分用户收费、幂等、模拟面试创建/断线/回合/结算等真实本地合成检查通过。
3. 发布保护测试 **37 passed**；探针自身单测 9 项也通过（已包含在候选 196 项中），网络隔离候选镜像探针 **18 项全部通过**。发布工具在独立评审发现 AST `Ellipsis`/`bytes` 哈希兼容问题后已修复，加入回归，并在真实完整源码上验证 overlay 结果逐字节匹配。
4. OpenSpec 严格校验、差异空白检查通过；文档链接在提交前核对。

不是完整项目套件零失败的声明。扩展回归发现四项既有模拟隔离失败，在原样导出的未修复线上源码中同样复现；本轮不修改这些非心跳方法，也不将本地主工作区的其它补丁一并发布。最终排除：

- `test_mock_interview_isolation.py::test_old_commands_fail_before_any_side_effect[start_live_session-kwargs9-False]`。
- 同一测试的 `control_capture-kwargs10-False` 与 `create_publisher-kwargs11-False`。
- `test_mock_interview_legacy.py::test_mock_tokens_cannot_use_normal_ingest_http_or_ws`。

前三项对应现有普通实时入口缺少模拟模式隔离检查，第四项对应现有普通发布者令牌检查缺少 mock 令牌隔离。已知问题应另开范围修复，不能解释为已通过这些隔离测试。本轮方法替换不改变上述路径。初次未提供隔离数据库时 11 项模拟 API 检查跳过；最终提供本机合成数据库后全部实际执行。最终的四项排除是已证明的原基线失败，不是新增失败。

所有数据库测试只使用本地 `127.0.0.1:55443/synthetic_heartbeat`（独立临时 PostgreSQL 容器/合成记录）；实际运行源码及私有配置未进入 Git。真实音频、用户资料、付费 provider 调用或生产压测均未用于自测。

## 同负载性能对比

每场三份合成资料；每组旧/新各 60 次心跳。旧操作从已校验哈希的实际运行方法提取，新操作使用实际源码候选；计时包括真实本地会话/资料 SQL，租约使用内存仓库，不含公网 HTTP、Redis 和生产排队。

| 并发 | 旧 P50 / P95 / P99（ms） | 新 P50 / P95 / P99（ms） | 旧/新失败 |
| --- | --- | --- | --- |
| 1 | 39.849 / 60.476 / 92.600 | 4.613 / 6.316 / 6.798 | 0 / 0 |
| 5 | 59.894 / 127.548 / 129.309 | 10.345 / 39.174 / 41.643 | 0 / 0 |
| 10 | 141.341 / 187.666 / 193.223 | 15.446 / 31.499 / 33.977 | 0 / 0 |

每组 60 次：会话读取 **120 → 60**、资料读取 **360 → 0**。不能将局部结果当作线上综合 P95 的降幅或 SLA。[对比驱动](../../scripts/benchmark_cn_web_heartbeat_restore.py)复用既有安全合成基准，只接受回环地址和隔离库。

候选相关回归执行目录为本机实际源码候选 `artifacts/cn-heartbeat-restore-20261014/candidate`，使用项目 `.venv/bin/python`、`PYTHONPATH=<候选>/apps/backend`、`OFFERSTEADY_DATABASE_URL=''`、`OFFERSTEADY_REDIS_URL=''`、`OFFERSTEADY_TEST_DATABASE_URL=postgresql://synthetic:synthetic-test-only@127.0.0.1:55443/synthetic_heartbeat`。运行测试清单见 [恢复任务](../../openspec/changes/lighten-cn-web-heartbeat/tasks.md)。

## 上线与回退条件

仅当本地证据绑定 Git 提交及同一源码哈希、候选镜像合成探针通过、运行镜像/环境/模型/Compose 未漂移、所有受保护任务两次检查为空时才切换 Backend。核对普通/模拟面试、准备页/页面租约、近期音频、未完成回答及资料后台任务；有活动则保持原服务。

回退只恢复当前 `567ddaf…` 镜像并重建 Backend，不回滚数据库或账本；Web、Admin、Worker、Redis 和 PostgreSQL 保持原容器。生产真实面试效果与同负载整体 P95 仍需用户上线后验收。

## 切换与上线检查证据

- 修复/测试/发布工具 Git 提交：`48fcabc460ac4093b92615e41e0e5997223c64e2`，切换前已推送到 `origin/codex/global-international-baseline-20260914`。发布记录标签：`release-cn-heartbeat-restore-20261015.1`。
- 实际新镜像：`offersteady-cn-backend:heartbeat-restore-20261014-1`，digest `sha256:ec510532ca598878e147c4277e6da9776924fbf056ed942ab4cc2bf110f398bb`。
- 回退标签：`offersteady-cn-backend:heartbeat-restore-20261014-rollback`，固定为切换前 `567ddaf…`（包含现有笔试会员和模拟面试能力）。本次无需回退。
- 独立候选镜像保留全部基线层，只新增单文件 COPY 层；只恢复一个已批准心跳方法。运行源码 SHA 与本地候选及镜像探针一致。
- 00:12:45 和 00:12:48 两轮切换门禁均通过：普通面试、近期准备、页面租约、近期音频、未完成回答均为 0；模拟面试仅 completed 27 条；受保护资料任务和 queued/retrying/running 作业均为 0。没有主动结束用户任务。
- 仅重建 `compose-backend-1`；模型、环境、Compose、资源限制、挂载不变，所有非目标容器的 ID/镜像/启动时间逐项不变。`current` 及旧健康版本字符串不作为新镜像标识。
- 00:14:27 核验：Backend healthy，RestartCount=0；实际方法调用 `heartbeat_idle_status`，不再调用 `get_session`/`reconcile_idle_session`。
- `/healthz`、`/login`、`/app`、`/app/mock-interviews`、`/api/v1/billing/status`、`/api/v1/mock-interviews/capabilities`、`/api/v1/web/state`、`/offersteady-build.json` 全部 HTTP 200。模拟面试 enabled=true；Web 仍为 `pricing-copy-hourly-20261011.1`。这里只确认可达及能力保留，不作为真人完整面试验收。
- 上线后短观察窗口 INFO 213、WARNING 2、ERROR/CRITICAL/Traceback 为 0；保留 `prepared.json`、`local-verification.json`、`candidate-verification.json`、`deployed.json`、`post-deploy-verification.json` 在服务器权限受限目录，私有配置不下载或提交。
- 本机专用 PostgreSQL 合成容器及 tmpfs 数据在验证后已移除，未清理生产数据或镜像。

能力场景核对使用本轮已执行的心跳专项与探针：一次投影/零资料、五字段 SQL 与软删除、403/404 无副作用、空闲边界与清理失败、结束下一跳拒绝、租约接管、非心跳资料变化校验均通过；发布保护与真实门禁/镜像核验覆盖安全切换场景。同负载合成证据见上表。
