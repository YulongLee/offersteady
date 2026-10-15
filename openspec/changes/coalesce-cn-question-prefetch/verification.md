# Local verification

第一阶段交付范围为本地开发、测试、实际国服源码候选和记录，生产发布由用户晚间另行决定。汇总见 [本地验收记录](../../../docs/releases/cn-question-prefetch-local-20261015.1.md)。

后续授权：2026-10-15 用户明确要求上线，已在五项活动门禁通过后完成 Backend-only 发布，见 [生产记录](../../../docs/releases/cn-question-prefetch-20261015.1.md)。原本地阶段限制不代表后来授权后仍未发布。

## Scenario coverage

| Spec 场景 | 对应本地证据 |
| --- | --- |
| 连续 partial 合并、首段及时执行 | `test_question_prefetch_scheduler.py::test_leading_starts_promptly_and_partial_burst_keeps_only_latest`、quiet/max-wait 测试、同负载 baseline/candidate 对照 |
| 相同文字 final 仍到达调度 | `test_realtime_question_detection.py::test_same_text_final_promotes_prefetch_without_duplicate_stable_event`、真实 Chat/scheduler 组合与独立阻塞对照 |
| 慢旧 partial 不阻挡空闲 worker 上的 final | `test_question_prefetch_scheduler.py::test_final_uses_idle_second_worker_while_obsolete_partial_is_blocked`、`test_question_prefetch_integration.py::test_real_chat_final_can_finish_before_blocked_partial_and_late_partial_is_not_cached` |
| 两 worker 都忙时全局有界 | `test_global_worker_bound_and_final_priority_with_both_workers_busy`、`test_queue_age_and_key_budget_drop_optional_work_without_extra_workers` |
| 会话清理、shutdown 撤销任务 | scheduler session-clear/shutdown、真实 Chat 组合、资源清理回归；独立 cleanup 竞态复查 |
| 迟到 partial 不覆盖 final | `test_late_partial_or_older_final_cannot_overwrite_final_stable_state`、旧 marker 的调度拒绝回归 |
| 清理和 observer 竞争、旧 cold observer 跨 reset | stable marker/generation 确定性回归、`cleanup-race-review-before.json` 与修复后的独立检查 |
| 点击不等预取，detail 仍独立检索 | `test_slow_prefetch_does_not_block_cache_miss_or_add_a_click_session_read`、foundation startup 单快照/并行 detail、阻塞预取的真实 stream 对照 |
| 同 selection revision 下文档版本/状态/集合变化 | `test_material_changes_invalidate_cache_even_without_selection_revision_change`、[12 项合成 eval](../../../ai/evals/question-prefetch-grounding.jsonl) |
| 身份/问题变化不接受子串复用 | cross-identity、完整问题/空白规范化回归，以及上述合成 eval |
| 慢旧资料不能覆盖新结果 | `test_same_revision_old_materials_cannot_overwrite_a_new_result`、`test_changed_materials_at_commit_are_not_cached`、提交/命中时撤销令牌回归 |
| 重复检索复用、过期不复活 | completed/in-flight 去重、generation TTL/容量、被淘汰运行任务迟到返回和真实失败回归 |
| warm/即时回答、当前资料引用 | `synthetic_comparison.py` 使用合成 provider 与当前版本引用；明确不测真实模型质量或线上 P95 |
| 保留普通/自动/Global/模拟/计费/字幕/生命周期行为 | 工作区相关回归、隔离 PostgreSQL/Redis 196 项、实际国服候选回归、未批准方法/路由/Prompt 字节保护清单 |

测试源码：

- [调度器回归](../../../apps/backend/tests/test_question_prefetch_scheduler.py)
- [Chat/scheduler 组合](../../../apps/backend/tests/test_question_prefetch_integration.py)
- [确定性清理竞态](../../../apps/backend/tests/test_question_prefetch_cleanup_races.py)
- [缓存回归](../../../apps/backend/tests/test_realtime_prefetch.py)
- [合成 eval 回放](../../../apps/backend/tests/test_question_prefetch_evals.py)
- [稳定问题观察器](../../../apps/backend/tests/test_realtime_question_detection.py)
- [资源清理](../../../apps/backend/tests/test_realtime_resource_cleanup.py)

最终冻结源码 SHA、准确命令、测试数量、已复现的旧版失败和保护清单位于本地记录及 `artifacts/cn-question-prefetch-20261015/verification/`。这些文件保留初跑失败和复测证据，不把扩展检查描述为全部通过。

本地阶段结果：工作区相关回归 255 项及独立清理竞态 6 项通过；隔离存储/模拟面试回归 196 项通过；实际国服源码候选 221 项相关回归及 16 项回答流程测试通过。合成相同输入检索为 41→2、会话读取为 41→3，点击仍一次授权快照且不等待阻塞预取。OpenSpec strict 校验、Markdown 链接及 diff 检查在交付前执行；当时线上状态未修改。

授权生产阶段：实际容器/167 文件无漂移；237 项候选测试再次通过，122 项门禁及 36 项切换/回退合成测试通过；生产隔离 probe、切换前五项门禁、切换后 live probe/140 条业务 HTTP 路径及健康检查通过。Backend `cc040a55…` 已生效，模型/环境/完整 HostConfig/挂载与其它七个容器保持。真实 P95 效果仍待用户测试和自然流量观察。
