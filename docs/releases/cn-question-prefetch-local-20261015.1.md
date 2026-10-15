# 国服问题预取优化：本地验收记录

本地阶段状态：开发和专项验收完成，当时未部署、未重启或更改线上服务。用户最初授权为先开发和本地自测，晚间另行决定发布。

后续状态：用户随后明确授权发布，2026-10-15 23:49（北京时间）已完成国服 Backend 更新，见 [生产发布记录](cn-question-prefetch-20261015.1.md)。本文其余内容保留本地验收阶段的范围与观测。

## 范围和基线

本轮对应 [OpenSpec proposal](../../openspec/changes/coalesce-cn-question-prefetch/proposal.md) 和 [执行清单](../../openspec/changes/coalesce-cn-question-prefetch/tasks.md)。目标是减少普通面试连续转写触发的重复资料查询，并防止过期问题或资料的预取结果被复用。

当前国服实际运行 Backend Image 的保存基线为 `sha256:eb242b56fded1473659c2f4517f07b42eeaff138b59029e5819fbaa972b12488`。源码位于本地 `artifacts/cn-mock-flat-billing-20261015/backend-candidate`，绑定证据为同目录上级的 `production-candidate-verification.json`。本轮只从工作区提取预取相关节点到该基线；当前工作区还含有其它已授权工作的变更，不能作为整包直接上线。

## 已实现行为

- 第一次稳定问题立即进入独立预取调度；中间更新合并为最新待办，默认静默窗口 350ms、最长等待 1500ms。Final 立即具备执行资格并优先于普通待办，有空闲第二 worker 时可以越过同问题尚未结束的旧 partial。
- 全局最多两个预取 worker，每个问题仅保留一个最新待办；最多 256 个问题键，待办超过 10 秒丢弃。会话清理和服务关闭会撤销待办及结果令牌，运行中的同步 IO 自然结束。
- 预取缓存核对用户、会话、问题 ID/revision、规范空白后的完整问题及资料指纹。文档版本、状态、索引状态、活动状态、集合变化都会使旧缓存失效；同 revision 的慢旧结果不能覆盖新资料结果。缓存及 generation 状态各限 128 个问题键，60 秒有效。
- 点击回答复用已经授权的会话快照，不新增点击读库，也不等待预取；详细回答仍走独立资料检索。字幕发布、现有 cold 队列、音频、模型、Prompt、计费和模拟面试路径保持原行为。

## 本地验证

执行中的回归、对照数据与实际基线候选保存在 `artifacts/cn-question-prefetch-20261015/verification/`。测试只使用合成资料和供应商替身；需要存储的测试使用本机隔离 PostgreSQL 和 Redis，未访问生产或真实模型供应商。

已完成的存储/功能回归：196 项通过，涵盖 Redis 重启恢复、国服/Global 模拟面试 API 隔离、国服每日免费和积分规则、60 分钟结束、任务竞争、音频/TTS 和资源清理。另补跑真实 PostgreSQL 轻量 heartbeat 投影 1 项通过。

更宽的工作区回归初跑为 335 passed / 3 failed / 1 skipped，未记作全绿：

- 微信生产禁用的错误码断言，以及 runtime 的 `latestBySource.microphone` 字段断言，两项在保存的实际国服旧基线独立运行也同样失败；本轮未修改相关逻辑，留为既有问题。
- provider prewarm 的 350ms 本地时间门限在并行负载下观测 400ms；停止其它测试后单项复测通过，实际旧基线单项也通过。保留初次失败记录，不用复测覆盖原始 XML。
- 初次 skipped 是未提供数据库的 heartbeat 投影测试，之后显式指定隔离 PostgreSQL 补跑通过。

原始证据：`local-regression.xml`、`baseline-known-failures.xml`、`local-prewarm-recheck.xml`、`local-storage-mock-regression.xml` 和 `local-heartbeat-postgres-recheck.xml`。

最终冻结工作区的相关回归 255 项通过（4.61s，包含 12 项合成 eval），另 6 项确定性 cleanup 竞态回归通过（0.28s）。独立审查发现并修复了两处清理/入队窗口，以及旧 provider 回调跨非退休 reset 的 generation 问题；第二代理复查 78 项通过，未发现新增阻断问题。新增用例覆盖首段、连续更新、final、慢旧任务、容量/TTL、资料变化、撤销提交、点击单快照和资源释放。

实际国服基线候选的 221 项相关回归和 16 项回答流程测试通过，均零失败、零跳过。候选测试启动真实 ASGI lifespan、使用字节一致的共享格式 JSON，并给一个 HTTP 已 mock 的契约测试提供保留的 `.invalid` 合成 URL；未为通过测试修改应用行为。测试进程在 collection/lifespan 前拒绝 socket connect/connect_ex/create_connection，并清空继承的供应商/数据库配置。准确命令、执行目录、耗时、源码 SHA 与返回码见本地 `candidate-verification.json`。当时完整候选的重放命令如下，依赖本地保存的实际镜像源码和证据目录：

```bash
.venv/bin/python artifacts/cn-question-prefetch-20261015/verification/run_candidate_verification.py
```

该命令只重放已生成的本地候选；需要重新生成候选时，先执行同目录 `build_local_candidate.py`。它严格校验保存基线的 SHA，拒绝把其它源码误当基线。两个脚本都不包含部署或 SSH 操作。这些历史候选和原始证据不随 Git 上传。

Git 中保留了[发布支持源码和纯合成回归](../../scripts/release_support/cn_question_prefetch_20261015/README.md)，克隆仓库后可直接执行：

```bash
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q scripts/release_support/cn_question_prefetch_20261015
```

## 同负载合成对照

序列为 41 次 partial 更新及 1 次 final，检索替身每次固定等待 30ms，断网运行。下列是一次可复现对照中的观测，不是实际供应商延迟或线上压测。

| 项目 | 原实际国服基线 | 本地候选 |
| --- | ---: | ---: |
| 被接纳的检索次数 | 41 | 2 |
| 会话读取次数 | 41 | 3 |
| 首段开始准备 | 1.56ms | 1.78ms |
| final 提交到当前结果准备好 | 647.77ms | 34.16ms |
| 预取阻塞时点击到首个可见合成答案 | 1.50ms | 0.78ms |
| 点击启动的会话授权读取 | 1 | 1 |
| warm quick 引用元数据数量 | 1 | 1 |

另一个独立用例让旧 partial 一直阻塞：候选能用空闲 worker 在约 3.85ms 内完成相同文字的更新 final；旧结果最终返回也不能覆盖它。资料版本变化但 selection revision 不变时，旧缓存被拒绝，新缓存引用合成 v2；完整问题变化不再接受子串命中。首字的亚毫秒差异只是本机样本，不作为首字性能改善承诺。

对照脚本和结果为 `synthetic_comparison.py`、`baseline-comparison.json`、`candidate-comparison.json`。Quick miss 在旧基线和候选都使用原有 fallback，detail 都读取当前资料并完整结束。未调用真实模型验证主观质量。

## 实际源码保护和冻结

候选相对实际国服基线仅改变 Chat、Realtime 和新增调度器三个文件。保护清单核对 177 个非批准方法、165 个其它文件、19 个路由模块和 20 个 Prompt 均保持原字节；两个 provider caller 仅插入生命周期 token 捕获/传递，剥离本轮插入后与原基线字节完全相同。原轻量 heartbeat、性能 ACK、计费和模拟面试方法保留。

工作区冻结 SHA256：

- Chat：`d95ad4af788ae4eaccd554fd41b69bef0ea8f98a773885f6bf35d3267e5942ae`
- Realtime：`b69fbad2f1efac2ee4e4990b7697305b972f6a90d985bc3961bd9d133a3ea9f8`
- Scheduler：`36bc5ab7fc2329945a3becdedc0ccc0a38356c334e8b32a735610c58774d744f`

本地实际基线候选的 Chat/Realtime SHA 与工作区不同，因为保留了实际国服的无关实现；候选的准确 SHA 保存在 `candidate-source-preservation.json` 和 `candidate-verification.json`，测试结束后已复核未漂移。候选不含 `.env`。未提交或推送本轮 Git、未打生产 tag、未构建或安装新助手，未操作线上数据库或服务。

## 证据和使用边界

本地比较可以验证被接纳的检索次数、会话读取次数、线程/待办上界、最终问题准备、点击不等待和资料引用版本正确性，不能推算线上整体 API P95 的实际降幅。夜间发布后仍需用真实流量观察检索量、连接创建速率、用户接口与遥测接口延迟。

缓存改为完整问题匹配后，较短 partial 与更长 final 不再互相复用，未命中沿用现有 quick fallback。现有客户端部分路径传入的问题 ID/revision 与预取键不一致，`question-stable` 也尚未被该客户端映射用于点击；这是原有命中率限制，本轮不扩展前端协议。合成命中测试使用正确绑定的 ID/revision，不能声称所有真实点击的命中率已改善。

现有 quick 资料组装仅把知识检索结果记录为引用元数据，没有把知识 chunk 正文追加到 quick Prompt；详细回答有独立检索。本轮保持这一行为，不声称通过本地替身测试证明真实模型回答质量或硬件麦克风端到端效果。

## 晚间发布前

用户另行授权上线后，应重新读取目标组件实际 Image 并检查相对保存基线的漂移，重新生成最小候选和回退包。继续保护已发布的 heartbeat/ACK 优化、国服模拟面试每天免费/100 积分/60 分钟规则、Global 原有权益和所有路由。此记录不代表已完成生产发布或真实流量验收。
