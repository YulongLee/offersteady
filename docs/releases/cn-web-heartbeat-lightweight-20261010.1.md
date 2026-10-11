# 国服页面心跳轻量化 — 2026-10-10

## 发布结果与范围

2026-10-10 01:05:11（Asia/Shanghai）完成国服后端切换。仅修改普通页面 `web-heartbeat` 的会话读取路径，不修改客户端或助手，不调整轮询频率。国际服未部署，未推送 Git。

- 正常心跳从两次完整会话读取改为一次五字段投影查询：会话 ID、所有者、状态、开始时间、最后活动时间。
- 正常心跳不再逐份刷新绑定资料，不读配置/对话/权益大字段，不写会话或计费记录。
- 保持不存在/无权限/已结束错误、空闲预警与超时清理、页面接管及租约响应。状态不缓存，结束后下一次心跳仍读取权威状态并拒绝续租。
- 非心跳的资料可用性校验、回答/截图、ASR、模拟面试、积分结算、模型、环境配置保持原路径。没有数据库迁移，也没有更改 Redis 数据结构。

开发依据：[提案](../../openspec/changes/lighten-cn-web-heartbeat/proposal.md)、[设计](../../openspec/changes/lighten-cn-web-heartbeat/design.md)、[能力场景](../../openspec/changes/lighten-cn-web-heartbeat/specs/lightweight-web-heartbeat/spec.md)。

## 本地自测

本轮心跳专项 27 项（含真实 PostgreSQL 测试）、发布保护 8 项通过；相关回归最终 **248 passed / 3 deselected / 0 skipped**，耗时 139.68 秒。覆盖原面试生命周期、计费、实时控制/清理/回收、模拟面试隔离和截图链路。候选镜像网络隔离合成检查 12 项通过，上线后对同一镜像再运行也通过。

没有宣称整套项目测试全部通过：首次扩展测试发现两项稳定的既有断言不一致和一项启动耗时波动。恢复 Git 基线的原心跳与原空闲读取逻辑后，两项稳定失败仍复现；耗时断言在新旧逻辑单独运行时均通过。最终相关回归明确排除以下三项，未为本轮修改其它功能：

1. `test_wechat_compatible_login_is_disabled_in_production`：期望旧错误码 `wechat-production-disabled`，当前返回 `domain_request_error`。
2. `test_realtime_runtime_tracks_frame_receipts_and_asr_status`：旧遥测断言读取 `latestBySource.microphone` 出现 KeyError。
3. `test_live_start_bounds_provider_prewarm_wait`：套件负载下偶发超过 350ms 的时限，单独复测通过。

真实数据库与负载测试仅连接本机回环地址的隔离 `synthetic_heartbeat` 库，全部是合成数据；没有连接生产库进行写入/压测，没有创建生产面试或扣积分。初次数据库尚未就绪的测试重试，在就绪后通过。

可复现验证命令（在项目根目录执行；数据库需先创建且仅允许隔离测试库）：

```sh
OFFERSTEADY_DATABASE_URL='' OFFERSTEADY_REDIS_URL='' \
OFFERSTEADY_TEST_DATABASE_URL=postgresql://synthetic:synthetic-test-only@127.0.0.1:55440/synthetic_heartbeat \
.venv/bin/python -m pytest \
  apps/backend/tests/test_web_heartbeat_lightweight.py \
  apps/backend/tests/test_cn_web_heartbeat_release_guards.py \
  apps/backend/tests/test_foundation.py \
  apps/backend/tests/test_interview_idle_lifecycle.py \
  apps/backend/tests/test_interview_usage_billing.py \
  apps/backend/tests/test_realtime_control_plane.py \
  apps/backend/tests/test_realtime_resource_cleanup.py \
  apps/backend/tests/test_realtime_session_reclamation.py \
  apps/backend/tests/test_mock_interview_api.py \
  apps/backend/tests/test_mock_interview_isolation.py \
  apps/backend/tests/test_mock_interview_legacy.py \
  apps/backend/tests/test_screenshot_inline_delivery.py \
  apps/backend/tests/test_screenshot_stream_admission.py \
  --deselect=tests/test_foundation.py::test_wechat_compatible_login_is_disabled_in_production \
  --deselect=tests/test_foundation.py::test_realtime_runtime_tracks_frame_receipts_and_asr_status \
  --deselect=tests/test_foundation.py::test_live_start_bounds_provider_prewarm_wait \
  -q -rs --tb=short --show-capture=no

openspec validate lighten-cn-web-heartbeat --strict
git diff --check
```

### 同负载性能对比

本机 PostgreSQL；每场绑定 3 份合成资料；每个并发档位旧/新各 60 次心跳。计时包含实际会话/资料 SQL，网页租约使用内存仓库，不包含公网 HTTP、Redis 和生产排队。没有人工添加延迟。

| 并发 | 旧 P50 / P95 / P99（ms） | 新 P50 / P95 / P99（ms） | 新旧失败数 |
|---|---|---|---|
| 1 | 37.541 / 59.380 / 82.030 | 4.528 / 6.225 / 7.075 | 0 / 0 |
| 5 | 82.171 / 111.792 / 117.630 | 12.340 / 14.887 / 15.471 | 0 / 0 |
| 10 | 144.557 / 163.097 / 167.340 | 18.203 / 33.171 / 33.191 | 0 / 0 |

每组 60 次心跳：会话读取 **120 → 60**，资料读取 **360 → 0**。局部心跳 P95 下降约 80%–90%，**不代表线上整体 API P95 会同比下降**。生产总指标受其它接口和最近五分钟请求构成影响，需用户实际测试后按接口对照。

性能脚本：[benchmark_web_heartbeat.py](../../scripts/benchmark_web_heartbeat.py)。其数据库校验拒绝非本机地址和非 `synthetic_heartbeat` 数据库；重复运行应使用全新隔离数据库。

### 逐项场景核对

| 能力场景 | 已执行证据 |
|---|---|
| 多资料正常心跳仅读一次，不刷新资料、不写会话/计费 | `test_heartbeat_reads_once_and_never_refreshes_materials`；候选隔离检查 |
| 五字段参数化查询，软删除返回 404 | 投影字段/SQL 单测；`test_real_postgres_projection_excludes_deleted_and_sees_fresh_state` |
| 错误归属 403，不更新活动或租约 | `test_denied_heartbeat_does_not_touch_activity_or_lease` |
| 原预警/过期边界，过期清理及失败不伪装成功 | `test_idle_boundaries_match_existing_calculation`；`test_expired_heartbeat_keeps_original_cleanup_and_error` |
| 结束后下一次心跳拒绝，不缓存 | `test_end_is_seen_on_next_heartbeat_without_cache`；真实 PostgreSQL 状态更新测试 |
| 准备页共用有效 live 租约；live claim / generation 不变 | `test_preparation_keeps_live_lease_and_live_claim_renews`；候选检查 |
| 非心跳读取继续刷新已变化资料 | `test_full_session_reads_still_refresh_changed_material`；候选检查 |
| 受保护任务存在时阻止切换；切换前重复门禁 | `test_cutover_has_two_idle_gates_before_tag_change`；生产门禁全零后切换 |
| 候选仅包含约定节点，环境/配置不变 | 5 文件 AST 白名单测试与发布时验证；上线镜像/source hash 比对 |
| 同负载合成性能，报告样本/分位数/失败数 | 上表及本机性能脚本输出 |

## 生产基线与切换证据

发布目录：`/opt/offersteady/releases/20261010-cn-web-heartbeat-1`。

| 项目 | 镜像标识 |
|---|---|
| 切换前实际后端镜像（保留回退） | `sha256:866a5e920cc8db962d9474ad3dff5995fd3348a17c3e2b2f778f9f1e43962384` |
| 新后端 `offersteady-cn-backend:web-heartbeat-20261010-1` | `sha256:2728cf3959771f813fcf7ea9fe86395ff1b94f731c3b5288a4decde65c66d496` |

以实际运行镜像为基线，仅移植五个文件中的批准类/方法；把新节点移除、两处修改恢复后，AST 必须等于基线。未把本地其它模型、TTS、文档解析、营销等脏工作区内容一起发布。编排/环境文件和既有组件指针未调整；后续发布需以运行容器镜像和本次 `prepared.json`/`deployed.json` 为准，不能仅依据旧目录源码判断当前版本。

- 单独预检及部署前两轮门禁全部通过：进行中面试、最近准备、有效页面租约、近 30 秒音频、未完成回答均为 0。
- 模拟面试仅有 completed 记录，无运行中流程；资料处理/删除/协调的 queued/retrying/running 任务与受保护资料任务均为 0。
- 仅重建 `compose-backend-1`；模型、环境、挂载、端口、资源限制和非目标容器的 ID/启动时间逐项不变。
- 上线后健康状态 healthy、RestartCount=0；检查窗口无 Traceback/ERROR/CRITICAL。上线后门禁仍全零。
- 公网 `/healthz`、`/login`、`/api/v1/billing/status`、`/api/v1/mock-interviews/capabilities` 均 HTTP 200；健康状态 ok；模拟面试 enabled=true、companionUpgradeRequired=false。
- 公网轻量检查耗时分别为 137/126/167/384ms，只是单次连通性验证，不能当作 API P95 或真实面试耗时。
- 候选及上线后隔离镜像探针均 12 项通过，未使用线上用户身份、简历或音频。

发布保护脚本：[release_cn_web_heartbeat.py](../../scripts/release_cn_web_heartbeat.py)；合成探针：[probe_cn_web_heartbeat.py](../../scripts/probe_cn_web_heartbeat.py)。私有配置备份仅留服务器，不输出或提交密钥/用户数据。

## 回退与用户验收边界

无 schema 或数据迁移。发布失败的自动回退恢复原镜像并仅重建后端；本次无需回退。后续手动回退也必须先重新确认无受保护用户任务，再将上述旧镜像恢复到运行标签 `compose-backend`，沿用原编排和环境，仅切换 backend。不要回滚数据库、账本或 Redis 数据。

真实用户麦克风、创建/进入/结束、快答/详细回答、截图、资料与计费体验仍待用户测试。建议在同样资料与使用方式下观察至少完整五分钟窗口，分别对照 `web-heartbeat` 与总体 API P95；不能仅凭低流量总分位数判断局部优化是否生效。

本机临时数据库容器 `offersteady-heartbeat-selftest-20261010` 与其合成数据卷在测试后删除；未清理任何生产容器、镜像或用户资料。
