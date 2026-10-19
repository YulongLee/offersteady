# Global Resume Optimizer verification — local + production, 2026-10-18

本变更共 46 个场景。2026-10-17 建立本地验证记录，2026-10-18 已追加实际候选镜像与国际服发布证据。以下逐项区分本地合成验证、实际镜像验证与线上验收，不把离线结果当成真实模型质量或生产会员实际生成。需求与最终决策见 [proposal](proposal.md)、[design](design.md)、[contract](contract.md)；本地汇总见[验收文档](../../../docs/releases/global-resume-optimizer-local-20261017.1.md)。

任务 28/28 已完成：本地开发/自测、最终冻结与实际镜像探针、国际服重复门禁/迁移/切换/独立验收及交接记录均有证据。生产发布详情见[实际发布记录](../../../docs/releases/global-resume-optimizer-20261017.1.md)。真实会员账号/模型生成效果仍由用户后续验收，不包含在生产匿名检查中。

## Evidence index

本地大产物留在原仓库，隔离 worktree 不复制真实环境或合成产物目录。以下链接指向本次实际本地证据位置：

| 代号 | 已检查的证据及范围 |
| --- | --- |
| B | Backend verification（历史证据：`artifacts/global-resume-optimizer-20261017/backend-verification/backend-verification.json`）：127 新测试、0 skip；其中 31 服务/API/资料流程、60 独立供应商/PG/并发、17 离线 AI 评测、19 表格源测试。源、测试与 eval hash 绑定。 |
| I | Independent live/optimizer integration（历史证据：`artifacts/global-resume-optimizer-20261017/backend-verification/isolation-record.json`）：主套后新增 1 项同进程实际执行器/任务运行时合成检查通过，生产源未变；共 128 个不同新检查，不宣称整个 128 项套件重跑。 |
| R | Qualified Global regression（历史证据：`artifacts/global-resume-optimizer-20261017/backend-verification/qualified-record.json`）：215 passed、0 skip；2 个 CN 私有 helper 假设在实际旧 Global 源同样失败，原非零结果与基线复现保留。 |
| A | Actual-source/full-schema proof（历史证据：`artifacts/global-resume-optimizer-20261017/backend-verification/candidate-proof.json`）：290 原文件中 284 不变、112 未批准 AST 保留；215 条原完整 API path 及 component schema 保留，新增 7 path/9 operation，共 222 path。既有 74 Prompt 和 auth/state/prefetch/实时/商业实现保留。 |
| W | Global Web proof（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/candidate-proof.json`）：223 passed、0 skip；类型/英文审计/生产构建通过；202 原文件、26 工作台函数与协议/状态协调器保留。 |
| C | Original Chrome 26（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/browser-smoke.json`）、export/save-error delta 6（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/browser-smoke-download-errors.json`）、final table/source delta 4（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/browser-smoke-table-source.json`）：1440/390 宽累计 36 场景；最终构建直接跑最后 4 项，前序结果依精确变更差异绑定，并非 36 全部跑最终版。 |
| H | Actual HTTP wire（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/http-wire-snapshot.json`）：实际 FastAPI/service/隔离 PG/root 格式模块共 25 响应；providerCalls=0；前端六个 wire 适配测试在 223 项内，不能重复计数。 |
| E | Real export QA（历史证据：`artifacts/global-resume-optimizer-20261017/export-qa/verification.json`）：11 个 root 格式测试，不计入 127；1 页和 3 页 DOCX/PDF 共 8 页渲染目视、文本提取、Unicode/嵌入字体通过。 |
| S | [Release-controller synthetic tests](../../../scripts/release_support/global_resume_optimizer_20261017/test_release_controller.py)：198 passed，覆盖六门禁、独立旧镜像执行、context/归属/完整 schema、反向 IO 拒绝、断流认领和 prepare 重入；无 Docker/SSH/真实 DB。 |
| P | Local full probe rehearsal（历史证据：`artifacts/global-resume-optimizer-20261017/probe-local-rehearsal/result.json`）：222 path/真实双格式通过；network、database、fileWrites、threadStarts、subprocesses、dependenciesResolved、lifespan 七计数全零。仅本地路径/合成配置替换，无真实密钥或生产环境。 |
| M | Actual candidate-image probe（历史证据：`artifacts/global-resume-optimizer-20261017/production-candidate-probe.json`）：最终冻结 302 文件、222 path、真实 DOCX/PDF，七类 side effects 全零、lifespan 未进入；最终 probe 为 `7180fa…`，P 的 `5f308e…` 只作本地历史。 |
| D | Prepare（历史证据：`artifacts/global-resume-optimizer-20261017/production-prepare.json`）、preflight（历史证据：`artifacts/global-resume-optimizer-20261017/production-preflight.json`）、deploy（历史证据：`artifacts/global-resume-optimizer-20261017/production-deploy.json`）、independent verify（历史证据：`artifacts/global-resume-optimizer-20261017/production-verify.json`）：2026-10-18 00:00:00.465 发布、00:01:25.259 独立 verify；固定镜像、完整源/静态/API/配置、五非目标及共享标签一致。生产公开路由四项 200、未登录优化 API/导出两项 401/private-no-store；未执行生产会员生成。 |
| O | Short production observation（历史证据：`artifacts/global-resume-optimizer-20261017/production-short-observation.json`）：Backend 263.23 秒、Web 227.65 秒，restart/ERROR/traceback/HTTP5xx 均 0；nonTargetsUnchanged=true，rawLogsExported=false。 |


下表中的测试函数名均可在隔离 worktree 的 [service/API tests](/Users/liyulong/.codex/worktrees/global-resume-optimizer/offersteady/apps/backend/tests/test_resume_optimizer.py)、[review/PG tests](/Users/liyulong/.codex/worktrees/global-resume-optimizer/offersteady/apps/backend/tests/test_resume_optimizer_review.py)、[table source tests](/Users/liyulong/.codex/worktrees/global-resume-optimizer/offersteady/apps/backend/tests/test_resume_optimizer_source.py)、[offline eval tests](/Users/liyulong/.codex/worktrees/global-resume-optimizer/offersteady/apps/backend/tests/test_resume_optimizer_evals.py) 和[export tests](/Users/liyulong/.codex/worktrees/global-resume-optimizer/offersteady/apps/backend/tests/test_resume_optimizer_export.py)中核对。

## Owned resume, membership and lifecycle

Spec: [scenario source](specs/global-owned-resume-optimization/spec.md)。

| 场景 | 当前状态 | 对应实际证据与边界 |
| --- | --- | --- |
| General review without a JD | 本地通过 | B/H/W/C；`test_service_e2e_quote_create_complete_edit_export_and_independent_save`，无 JD role matching unassessed。 |
| Versioned resume and JD | 本地通过 | B/H；`test_jd_matching_requires_two_correctly_bound_sources`、版本/owner/kind 防护；Web 只传所选 JD 模式与版本。 |
| Invalid or foreign input | 本地通过 | B；`test_bad_source_rejected_before_allowance_or_provider`、`test_version_row_must_match_document_owner_identity_and_kind`。 |
| Parsed resume contains a MinerU HTML table | 本地通过 | B/H/C；`test_table_cells_rows_contacts_entities_and_line_breaks_keep_all_visible_content`、`test_html_table_resume_is_normalized_before_model_evidence_and_real_dual_export`；原 Parser/产物 hash 保持。 |
| Source contains unsupported or executable HTML | 本地通过 | B/H/C；`test_unknown_or_ambiguous_markup_is_rejected_without_dropping_facts`、`test_unsupported_source_markup_fails_before_quota_and_provider`，次数/provider 均未触发。 |
| Member uses the daily free optimization | 本地通过 | B/H/W；`test_only_current_non_free_time_members_are_eligible`、`test_one_day_member_cross_midnight_replay_survives_expiry_without_second_use`，含 1 天会员。 |
| Non-member requests optimization | 本地通过 | B/H/W/C；`test_nonmember_and_quote_mismatch_never_read_documents`，升级会员且无积分/单次付费入口。 |
| Member exceeds daily allowance | 本地通过 | B/H/W/C；同日 reserve/settled 拒绝第二次，展示下一 UTC 日重置。 |
| UTC day boundary | 本地通过 | B；`test_previous_day_release_never_creates_extra_current_day_allowance`、跨日幂等重放。 |
| Duplicate creation or completion | 本地通过 | B；E2E 幂等创建、重复结算，`test_concurrent_admission_cannot_double_reserve_the_last_use`。 |
| Generation fails or is cancelled | 本地通过 | B/I；`test_runtime_failure_cancel_shutdown_release_and_no_late_revive`、`test_cancel_delete_and_source_delete_block_late_completion_and_release_once`。 |
| Concurrent claims for the last free use | 本地通过 | B；`test_concurrent_admission_cannot_double_reserve_the_last_use`，独立 PG 并发。 |
| Owner edits and downloads after membership expiry | 本地通过 | B/H/W；`test_edit_and_save_as_remain_available_after_membership_expiry_and_are_revision_safe` 及页面 expired-member 下载；不新占次数。 |
| Duplicate create is replayed | 本地通过 | B/H/W；原任务/原 key 一致重放，无第二模型 work；跨日/到期重放保持。 |
| Capacity is exhausted | 本地通过 | B/I；`test_cross_repository_claim_is_global_single_running_and_capacity_is_bounded`；1 running、8 unfinished 和同账号 1 unfinished。 |
| Provider fails or process is interrupted | 本地通过 | B；`test_provider_failure_is_bounded_safe_and_never_retried`、`test_stale_lease_fails_without_reclaim_or_double_release`，无真实 provider。 |
| User cancels work | 本地通过 | B/H/W/C/I；`test_runtime_cancels_active_http_and_safely_finishes_without_retry`，取消退创建日次数且迟到结果不复活。 |
| Another account accesses an optimization | 本地通过 | B/H；`test_foreign_job_operations_are_safe_404`，覆盖任务、编辑、导出、另存、取消与删除。 |
| Source is deleted during generation | 本地通过 | B；`test_cancel_delete_and_source_delete_block_late_completion_and_release_once`，源删除与清理同事务、late claim 拒绝。 |
| Task is deleted after completion | 本地通过 | B/H/W；`test_completed_delete_purges_personal_fields_but_does_not_refund_use`、独立另存保留；personal fields 清空。 |
| User starts the workflow | 本地通过 | W/C/H；处理同意、保存/删除说明、ready/owned 资料选择与事实核对确认可见。 |
| Provider or storage error is logged | 本地通过 | B/H/W；`test_provider_failure_is_bounded_safe_and_never_retried`、导出安全错误、私有 422/固定英文提示，不返原文/provider exception；无真实 provider 日志验收。 |

## Grounded review, editing and exports

Spec: [scenario source](specs/grounded-resume-review-and-export/spec.md)。

| 场景 | 当前状态 | 对应实际证据与边界 |
| --- | --- | --- |
| Review has evidence for findings | 本地通过 | B/H/W；`test_reference_score_is_server_mean_and_unchanged_sections_survive`、literal evidence 校验；总分服务端等权计算。 |
| No JD was supplied | 本地通过 | B/H/W/C；四维评分、role match 未评估，不把缺失维度记零。 |
| Review schema or evidence is invalid | 本地通过 | B；`test_score_rejects_coercion_and_out_of_range`、`test_evidence_cannot_be_invented_or_rebound`、invalid shape/English/长度校验。 |
| Achievement lacks a metric | 本地通过 | B；`test_unsupported_metrics_dates_skills_and_agency_are_rejected`、离线 grounding eval；缺失成果只进 missingFacts，不填虚构数字。 |
| JD requests an unsupported skill | 本地通过 | B；双来源匹配与新增实体/技能拒绝、离线 eval；JD 不作为候选人事实。 |
| Source contains prompt injection | 本地通过（离线） | B；专属 Prompt 把资料标为不可信、合成注入/伪造输出守卫；未测真实模型抗注入成功率。 |
| Owner edits a successful draft | 本地通过 | B/H/W/C；E2E draft revision 与初始 review 分离，改后需重新事实确认，原资料/旧快照保持。 |
| Stale draft save | 本地通过 | B/H/W/C；`test_revision_conflicts_and_unconfirmed_exports_do_not_render_or_charge`；UI 保留未保存编辑。 |
| Download both formats | 本地通过 | E/B/H/W/C/P；真实 OOXML/PDF magic/MIME/UTF-8 filename/完整内容，重复下载不占次数。 |
| Long resume export | 本地通过 | E；`test_long_pdf_and_docx_keep_final_marker_and_every_bullet`；各 3 页、共 8 渲染页逐页目视，非 HTML 改名。 |
| Deleted or unfinished export request | 本地通过 | B/H；`test_delete_racing_export_blocks_return_and_physically_purges`、`test_export_rechecks_owner_source_and_revision_after_renderer`。 |
| Save and reuse optimized material | 本地通过 | B/H/W/C；`test_save_as_enters_real_durable_document_processing_and_becomes_selectable`、`test_save_as_and_source_delete_are_serialized_before_copy_confirmation`。 |
| Replay save as | 本地通过 | B/H/W；同 job/revision deterministic IDs、重复另存不重复对象/资料/处理提交，旧独立版本保留。 |

## Isolation and protected release

Spec: [scenario source](specs/global-resume-optimizer-safe-release/spec.md)。

| 场景 | 当前状态 | 对应实际证据与边界 |
| --- | --- | --- |
| Optimizer work is queued while an interview is running | 本地通过（有限合成） | I；实际占满 LiveAnswerStreamExecutor 同时运行 actual ResumeOptimizerRuntime；双方取消/容量释放、live reconnect、optimizer 单 running 与次数结算互不串用。非真实模型容量/P95 证明。 |
| Feature disabled or Chinese deployment | 本地通过 | B/W；`test_auth_and_disabled_capability_need_no_provider_or_repository`、Global-only gates；CN/Admin/desktop 无发布。 |
| Run optimizer verification | 本地通过 | B/R/E/W/C/H；独立 Prompt/合成 eval，真实 provider=0；逐项命令/返回码保留。 |
| Repeat migration or roll back application | 实际增量迁移通过；回退仅合成验证 | B/S/D；实际发布经 checksum/事务锁执行0053，仅新增功能表；固定旧镜像/上下文保留。未触发生产回退或破坏性 down migration。 |
| Self-test before packaging | 本地与实际镜像通过 | B+I/R/E/W/C/H/P/M；冻结 Backend353 原记录保持，额外1项同源增量；最终实际镜像302文件/222路径及双格式通过，5.3完成。 |
| Baseline or non-target drift is detected | 合成拒绝通过；线上一致 | S/D/O；合成 image/source/config/shared tag/non-target/fullcontext 漂移均拒绝；实际独立 verify及短观察无漂移，未知归属不认领。 |
| Existing Global capabilities are verified | 本地与实际镜像/线上核对通过 | A/R/W/M/D；实际222 paths=215旧+7新，旧 component、74 Prompt、auth/state/prefetch/商业实现保持。会员授权业务行为为本地合成验证，未调用生产模型。 |
| Real user remains active | 合成拒绝通过；实际空闲门禁通过 | S/D；活跃/未知/读取错合成反例均拒绝，partial可安全resume；实际预检与紧邻切换重复六道独立旧镜像门禁通过，未结束或清理用户会话。 |
| Idle verified deployment | 实际发布及独立验收通过 | D/O；仅Global Backend/Web固定镜像切换，完整源/静态/routes/config及五非目标/共享标签核对，短错误统计全部0。 |
| Candidate fails verification | 合成恢复分支通过；生产未触发 | S/D；可识别own health/public failure才独立门禁恢复；漂移停止，固定旧image/冻结上下文保留。实际发布成功，未执行生产故障回退演练。 |
| Global release is reported | 发布记录与入口/规则交接完成 | D/O及实际发布记录；时间/固定身份/验收/会员UTC每日1次/限制已记录，用户可进入国际服测试；真实模型与个人账号效果待用户验收，CN需后续授权。 |

## Actual production acceptance added on 2026-10-18

Global Backend/Web 已于 **00:00:00.465（Asia/Shanghai）** 发布，**00:01:25.259** 独立 verify。实际 Backend 镜像为 `sha256:991cabbc65ddec642f1790370b0977f75e5c40e92581ff632de012f960120135`，Web 为 `sha256:5b22cd0be64274937c15d51174a25b0063de8af272d848c0c80c3460952648f4`。18 个批准 Backend 输入基于实际旧镜像；最终实际302文件、222完整路径和Web217静态路径合格。64个最终Web输入来自proof清单，旧静态路径/hash资源保留，历史30个中间文件未入发布。

预检和切换邻近重复独立旧镜像只读活动门禁通过，增量0053迁移及固定镜像发布完成。仅启用本功能flag，既有有效环境/配置/HostConfig/挂载/Nginx/模型、五非目标和共享标签保持；所有完整源与API核对通过。私有配置留服务器，未导出原始用户日志或资料。

生产仅验证公开页面/health/build入口200，以及未登录capabilities与合成无效job导出401/private-no-store；没有创建或使用生产会员测试账号，没有生产模型调用。带授权任务/会员/编辑/下载/删除/另存能力的证据仍是 B/H 的本地真实API/隔离PG与受控合成结果。M在实际候选镜像中验证真实格式与完整应用schema，不进入生命周期或业务依赖。

截至 **00:03:43.289** 的观察：Backend 263.23秒、Web227.65秒，两者running且restart0，Backend healthy；Web未配置独立容器health。ERROR/traceback/HTTP5xx全部0，非目标身份保持。该短观察不是长期稳定性/P95证明。未触发生产回退；恢复与漂移拒绝仅做合成分支验证。

任务28/28已按上述真实边界完成，未归档/提交/推送。已交接[国际服入口](https://offersteady.com/app/resume-optimizer)与会员规则，用户后续检查本人会员账号的真实生成、编辑和下载体验；国服需国际服验证后的另行授权。

## Verification limits and user acceptance

- 冻结发布包的 `verified.backendTests=353` 对应 127 新主套 + 215 适用旧回归 + 11 格式检查，原通过记录/manifest 保留。其后独立同进程隔离增量 1 项通过，生产源 hash 未变；本地不同 Backend/格式检查共 354，新 Backend 为 127+1=128，均为分批结果而非全集重跑。适用旧回归 215 项、0 skip；不把旧基线失败转为通过，不将格式 11 项或 wire 6 项重复计数。
- Chrome 36 项是 26+6+4 三阶段累计，最后 4 项直接绑定最终 build entry/hash；保留前序构建证据及精确差异，不能宣称 36 全部跑最终源。原 CSP 有既有 inline script 拒绝，无新增违规。
- 所有测试资料为合成；没有真实模型质量/抗注入成功率、用户个人内容夹具、生产负载、实体设备或长期 P95 验收。同进程有限合成隔离不等于真实供应商容量保证。
- P 保留本地rehearsal历史；实际生产镜像探针以M为准，私有冻结/重复门禁/发布与独立verify以D/O为准，5.3及6.x已完成。未更新CN/Admin/desktop，未提交推送Git。
- 本次实际镜像身份、重复门禁、迁移/切换/健康/路由/配置/非目标及短脱敏错误统计已追加；真实会员账号与模型质量由用户后续验收，不能将匿名401和本地合成成功解释为生产授权生成已测。任何后续变更仍须保护活跃/未知用户工作。
