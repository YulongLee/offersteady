# 国际服问题预取优化本地验收 — 2026-10-16

用户已明确要求把本轮国服问题预取优化同步国际服并上线。本记录保存上线前本地实际源候选与专项验证，对应 [OpenSpec 提案](../../openspec/changes/sync-global-question-prefetch/proposal.md)、[预取与产品隔离规范](../../openspec/changes/sync-global-question-prefetch/specs/global-question-prefetch-parity/spec.md)和[发布保护规范](../../openspec/changes/sync-global-question-prefetch/specs/global-prefetch-protected-release/spec.md)。其后实际镜像探针、即时活动门禁及 Global Backend 生产切换均已完成，见 [2026-10-16 生产发布记录](global-question-prefetch-20261016.1.md)。

## 范围和国际服保护

仅迁移 Global Backend 普通面试的问题预取、缓存和相关生命周期节点：首段及时准备，连续更新合并为最新待办，final 优先，固定两个 worker；最多 256 个调度键、350ms quiet、1500ms max wait、10s pending TTL。缓存最多 128 个问题、60s 有效期，按当前 owner/session、完整问题及资料版本/状态/活动/集合校验。点击快答保持原来的非等待和 fallback，详细回答独立检索；清理、reset 和 shutdown 撤销旧任务及结果。

Global 七天及以上购买套餐准入、UTC 每日三场及原有独立会员规则保持，不加入国服积分收费或 60 分钟自动结束。语言、模型/Prompt、TTS、Creem、普通/模拟隔离、既有 heartbeat/ACK 优化保持；线上模拟面试开关原为 `false`，继续保留。Web、Windows/macOS 助手及 1.3.5 下载清单、Admin、worker、数据库/Redis、国服不在本轮发布范围。无新增依赖、数据库结构迁移、用户数据清理或音频/转录持久化。

## 实际源基线和最小候选

实际运行 Global Backend 基线镜像为 `sha256:1dab56432de7606b172e30c84033e82fc44a236015c1e21a6ad0826e33be6348`，容器为 `c87d92ce07300e7e34af617d8fe378f0db55f7b4c83ee492c7f584f4e17d7efc`。重新采集的 app/Prompt 共 235 个文件与重建基线全部匹配；候选为 236 个文件，仅变更两个既有服务文件并新增一个调度器，另外 233 个既有文件逐字节保持，包含全部 74 个 Prompt 和 19 个模块路由文件。

| 候选文件 | SHA-256 |
| --- | --- |
| `services/chat_service.py` | `46d9db278aadc4eae36f8a17552ee307e9ddcdbd386c8d3f4297f86b70b8f890` |
| `services/realtime_speech_service.py` | `d344c6089035fe5fd1a33a82425cc28637acf362447fb745ba5ab80e28594e69` |
| `services/question_prefetch_scheduler.py` | `36bc5ab7fc2329945a3becdedc0ccc0a38356c334e8b32a735610c58774d744f` |

170 个原有受保护方法逐字节不变，六个既有 caller 的定点字节修改可以逆向精确还原；两文件除批准节点外的完整 AST 与基线一致。候选保留 Global 的 cleanup lock、retired-session 清理及 provider caller 既有行为。初次移植发现缺失 `_session_is_retired` 依赖，已仅加入八行只读内存 helper，使用原有 `_frame_worker_lock` 和 retired set；未引入国服其它退役/孤儿清理行为。上述为修复后冻结 SHA，旧候选失败证据保留。

证据位于本地 `artifacts/global-question-prefetch-20261016/baseline-reconstruction.json`、`verification/candidate-source-preservation.json` 和 `verification/candidate-module-boundary-proof.json`。共享 Git 源包含其它区域研发内容，不能整文件或整包覆盖本实际源候选。

## 已执行本地验证

| 验证 | 结果 |
| --- | --- |
| 实际 Global 源候选主专项 | 224 个测试案例通过，另有 16 个 unittest subtests 通过；JUnit 合计 240 条 |
| Global 权益、语言、回答与普通收费相关回归 | 63 通过 |
| 专用本机 PostgreSQL/Redis：Global 模拟、网页 heartbeat 和 Redis 恢复 | 44 通过 |
| 以上候选案例合计 | **331 通过**，另计上述 16 个 subtests |
| 回答流程 foundation 专项 | **16 通过**，单独计数 |
| 发布控制器和活动门禁保护回归 | **184 通过**，包含五项直接 `verify_live` 健康/重启异常拒绝 |
| 独立候选与锁序审核 | 源码保护、实际服务构造/observer/调度/clear/reset/shutdown 合成调用通过 |

无存储测试阶段拒绝全部网络连接；存储阶段仅允许 `127.0.0.1:55445` 的专用合成 PostgreSQL 和 `127.0.0.1:56385` 的本机 Redis，使用 `synthetic_global_prefetch_20261016`、`synthetic_heartbeat_prefetch_20261016` 等隔离测试库。没有连接生产数据库、调用真实模型/音频供应商、复制真实用户资料或创建线上面试。

独立审核实际构造 Global 服务并验证 observer 进入真实调度器、clear 撤销 callback token、reset 后旧 generation 被拒绝及新 generation 可用、retired reset/shutdown 拒绝迟到任务。确定性并发验证在持有 stable lock 时让实际 `_reset_realtime_session` 进入 clear，仍能在 250ms 内获取 frame lock；释放 stable lock 后 reset 在两秒内完成，证明既有 reset 先释放 frame lock 再进入 stable 清理，没有发现反向锁环。证明在本地 `verification/independent-review.json`。

## 合成对照结果

同一组 41 次 partial 更新和一次 final，实际基线/候选使用固定合成 provider：

| 指标 | 实际基线 | 候选 |
| --- | ---: | ---: |
| 检索调用 | 41 | 2 |
| 会话读取 | 41 | 3 |
| final 提交后资料就绪 | 677.0ms | 36.8ms |
| 阻塞预取期间点击首个可见内容 | 1.6ms | 2.1ms |
| 点击启动会话读取 | 1 | 1 |

候选 leading 约 2.0ms 开始；旧 partial 阻塞时 final 可使用空闲第二 worker，final 完成后旧结果不能覆盖。已有准备时间的 quick 引用合成资料 v1，资料版本变化而 binding revision 不变时拒绝旧证据，刷新后 detail 使用 v2；完整问题匹配要求通过。以上是本机合成时序与固定延迟结果，仅证明工作合并、非等待和资料引用行为，不能直接推算线上整体 P95 或真实模型回答质量。完整对照在本地 `verification/baseline-comparison.json` 和 `verification/candidate-comparison.json`。

## 既有差异与测试适配边界

本轮没有宣称全仓测试全绿。更宽共享测试中，部分案例要求国服后续 cleanup lock/orphan API、不同普通收费接口，或以 `object.__new__` 省略 Global 实际构造字段；未适配版本在原 Global 基线同样失败，详见本地 `verification/baseline-known-differences.json`、`verification/wider-results/`。已有 Global 模拟库没有国服 `duration_deadline` 接口，当前共享案例的同一失败已在基线重现，见 `verification/baseline-known-storage-difference.json`；补充的 Global 实际 `get`/generation 场景验证超过 60 分钟仍保持原行为，没有给产品代码加入该国服接口。

测试专用副本只适配 Global 原有内存退役操作及 legacy ACK fixture 必需字段，两份副本全部断言 AST 保持；ASGI 测试进入实际 lifespan，合成远程网关配置使用保留测试域名。共享 eval、migration 和格式资产仅供隔离本地测试，不进入三文件生产载荷。适配清单在本地 `verification/test-support-adaptations.json`，结果在 `verification/candidate-verification.json` 和 `verification/candidate-storage-verification.json`。

## 发布保护和后续验收

[Global Backend 发布控制器](../../scripts/release_global_question_prefetch.py)及[活动门禁与保护回归](../../scripts/release_support/global_question_prefetch_20261016/README.md)保存于源码。控制器冻结全部实际 Compose/Env 文件及完整渲染配置，仅以私有固定镜像 ID overlay 变更 Backend；五项只读门禁须覆盖普通/笔试/模拟、页面/桌面租约、音轨、回答/截图与资料工作，缺字段、非整数/非零保护计数或异常退出均拒绝切换，回退同样检查新活动及本轮归属。原始诊断与密钥配置只留服务器私有目录。

本地已独立复核控制器 SHA-256 `ca4cfc746b058bb5750b64dac6a76e22d520154f995a8bc9cd5a5181d659c0f6`。随后候选实际镜像已在 `network none`、只读文件系统、`cap-drop ALL` 和 `no-new-privileges` 下通过探针，详见生产记录；Python IO guard 只保护经过审阅的普通代码路径，不能替代容器隔离。

生产任务已按实际执行结果更新 [任务清单](../../openspec/changes/sync-global-question-prefetch/tasks.md)。真实流量下 P95 改善、长期稳定性、Windows/macOS 实机收音或真实模型主观效果仍待后续用户验收；本轮不包含生产回退演练。
