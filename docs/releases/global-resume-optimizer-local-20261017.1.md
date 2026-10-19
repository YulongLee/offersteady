# 国际服简历优化本地验收 — 2026-10-17

后续更新（2026-10-18）：国际服已实际发布，见[生产发布与独立验收记录](global-resume-optimizer-20261017.1.md)。下文保留 2026-10-17 本地验收时点的状态和限制，文中的“待执行”不代表当前发布状态。

本轮完成 Global 简历优化的本地开发和合成自测，已具备评分建议、可编辑优化稿、另存新简历及真实 Word/PDF 下载。**本文件记录本地验收；实际候选镜像探针、最终冻结及线上发布验收仍待执行，不代表已经上线。** 对应[需求](../../openspec/changes/add-global-resume-optimizer/proposal.md)、[最终接口与会员合同](../../openspec/changes/add-global-resume-optimizer/contract.md)、[逐场景验证](../../openspec/changes/add-global-resume-optimizer/verification.md)。

## 已确认行为与范围

- 仅 Global 的有效付费时间会员可新建优化，包括 1 天套餐；按 UTC 每日免费 1 次。非会员提示升级，当日超额提示下一 UTC 日；没有积分、新钱包或单次付费入口。失败、取消或源删除导致未交付时，幂等释放创建日次数，跨日不多退；已成功任务删除不返还成功次数。
- 从自有 ready 简历中选择或沿用既有上传流程，可添加目标岗位、自有 JD 或粘贴 JD。无 JD 明确不评估岗位匹配。资料、任务、编辑、下载、另存和删除均在服务端校验 owner、版本与源存续状态。
- 展示本工具标准下的 0–100 参考评分、维度理由、原文依据、建议及待补充信息，不承诺录用概率。专用英文 Prompt/合成评测与实时面试分离；通过原文局部替换保留未改动经历、数字、日期、联系方式及其他段落，JD 要求不会直接成为候选人经历。
- 用户可比较源文与 AI 初稿，编辑时使用 revision 防覆盖；下载/另存前需确认事实。编辑、导出、另存不占新次数，会员到期后仍可操作未删的既有完成稿。另存创建独立资料，通过原有正常处理流程变为可选，原简历和既有面试快照不改。
- 兼容 MinerU Markdown 中的受控惰性 HTML 表格：仅优化输入读取器转换行/单元格/换行，保留全部文字、实体、数字及联系方式；显示源文、模型输入和 quote 验证使用同一副本。原始文件、Parser 产物和旧 Parser 代码不变；未知/破损/可执行 HTML 在次数预留和模型调用前明确拒绝，不静默丢内容、不执行或抓取资源。
- 独立有界任务：每账号最多 1 个 queued/running、全局最多 8 个未完成、最多 1 个模型请求；独立客户端、90 秒超时、队列 15 分钟期限。重启/超时/取消不自动重放模型。删除任务或引用的简历/JD会取消并清空派生内容，迟到结果不能复活；用户已明确另存的独立简历按自身资料删除规则保留。

## 真实基线与保护

候选以此次只读核对的实际 Global 组件为基线，未从混合 Git 源覆盖整服：

| 组件 | 实际运行镜像 |
| --- | --- |
| Global Backend | `sha256:c0503cb8a166dc4cfb64e3d4ca1f98792e788cdb29147d8282a8e43d0146726a` |
| Global Web | `sha256:ab7706981124579a9fb6e703702202c299817af1a78330068637bd7ba6eaca0c` |

Backend 证据（历史证据：`artifacts/global-resume-optimizer-20261017/backend-verification/candidate-proof.json`）绑定 290 个实际原文件，其中 284 个逐字不变；五个批准既有文件只接入新功能，另有 root 维护的依赖变更。112 个未批准函数 AST 保持；既有鉴权/状态读取、问题预取、实时面试、商业逻辑及全部 74 个既有 Prompt 保持。实际完整 OpenAPI 的 215 条原路径及所有旧 component schema 保留，新增 7 条路径、9 个 HTTP 操作，共 222 条路径。

Web 证据（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/candidate-proof.json`）绑定实际发布源恢复与构建基线；五个既有文件只增加入口/路由，202 个原文件、26 个工作台函数、状态协调器及协议保持。构建保留 `en-US`、既有 Creem 开启配置及生产 API 路径。部署输入取 proof 绑定的最终 64 个构建文件，排除历史 `candidate-static/` 中残留的 30 个中间版本文件；计划从实际 Web 镜像叠加并保留原 200 个静态路径及旧 hash 资源，不用残留目录全量覆盖。该保留方案仍需实际镜像验收，不能用本地目录代替。

国服、Admin、伴随程序均不在发布范围；没有提交或推送 Git。现有 Global 账户、语言、Creem、会员、分钟及模拟面试开关/配额不随本功能改变。

## 已运行验证

| 范围 | 实际结果 | 证据与说明 |
| --- | --- | --- |
| 新 Backend/API/任务/PG/离线评测 | 主套 127 passed，0 skipped；另 1 项同进程隔离增量通过 | 31 服务/API/正常资料处理和表格导出、60 独立供应商/PG/并发、17 离线事实与否定边界、19 表格输入测试；额外隔离增量源未变，共 128 个不同检查，不宣称 128 全套重跑；完整记录（历史证据：`artifacts/global-resume-optimizer-20261017/backend-verification/backend-verification.json`） |
| 适用的既有 Global 回归 | 215 passed，0 skipped；2 个明确排除的原基线失败 | 覆盖 Global 账号、邮件/密码、Creem、会员、资料、鉴权/状态、预取/实时；原可选 PG 用例在独立 schema 启用并另行通过，见适用集记录（历史证据：`artifacts/global-resume-optimizer-20261017/backend-verification/qualified-record.json`） |
| root 独立格式测试 | 11 passed | 与 127 项不重复计数；真实 DOCX/PDF、内容提取、字体、格式拒绝，见格式验收（历史证据：`artifacts/global-resume-optimizer-20261017/export-qa/verification.json`） |
| Global Web | 223 passed，0 skipped | 类型检查、英文 copy audit、生产构建通过；包含 6 个实际 HTTP wire 适配测试，见 Web proof |
| 实际 Chrome | 26 原流程 + 6 导出/另存失败增量 + 4 表格文案增量，共 36 个累计场景通过 | 1440/390 宽度、合成账户与资料、真实附件字节、外部请求阻断；**最后构建直接运行的是最后 4 个场景**，其余结果依精确变更差异绑定，不能声称 36 个全部重跑于最终版 |
| 本地实际 HTTP wire | 25 个响应，模型调用 0 | 真实 FastAPI router/service、隔离 PG、root 格式模块；wire 快照（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/http-wire-snapshot.json`） |
| 发布控制器安全合成测试 | 198 passed | 独立旧镜像门禁、未知/失败拒绝、完整 context/归属保护、切换/回退/断流认领/prepare 重入；[测试源](../../scripts/release_support/global_resume_optimizer_20261017/test_release_controller.py) |
| 完整本地 probe rehearsal | passed；222 条 HTTP 路径；真实 DOCX/PDF | 原探针仅替换本地路径/合成期望；七类 side effects 全零、未进入生命周期；结果（历史证据：`artifacts/global-resume-optimizer-20261017/probe-local-rehearsal/result.json`）。这是本地 Python rehearsal，尚非最终生产镜像探针 |

已上传冻结发布包的 `verified.backendTests=353` 对应 127 新主套 + 215 适用旧回归 + 11 格式检查，原通过记录与 manifest 不重写。其后同生产源码增加 1 项独立隔离回归通过，因此本地共有 354 个不同 Backend/格式检查，新 Backend 为 127+1=128 个不同检查；这些为分批执行，不是 354 或 128 项全集一次重跑。

最初未筛选既有集为 214 passed、1 skipped、2 failed。两个失败在冻结的实际旧 Global 源上完全复现：`test_cleanup_after_initial_retired_check_cannot_recreate_stable_state` 和 `test_cleanup_and_final_admission_are_one_memory_transaction` 依赖 CN 私有 `_retire_session_id`，原 Global 不存在。未改生产面试代码去适配它们，也未把初次非零结果改成通过；原日志/JUnit、基线复现及最终适用集分别保留。初次 skip 已在最终适用集和独立 PG 检查覆盖，不能据此声称全仓全绿。

格式验收实际生成 1 页及 3 页 DOCX/PDF，双格式共 8 页渲染并逐页目视检查，末段/列表/数字/联系方式完整。拉丁重音、中文、日文、韩文合成姓名通过，PDF 嵌入字体；DOCX 在隔离字体配置下以 Arial 与附带 OFL Noto CJK 渲染，其他读者仍可能替换字体。PDF 使用 ReportLab 4.4.9 和附带 OFL 字体，DOCX 由标准库生成 OOXML，无远程资源或 HTML 假附件。不支持的字符/格式明确失败而不产出缺字成功稿。

Chrome 三阶段证据分别为 26 原流程（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/browser-smoke.json`）、6 导出/另存失败增量（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/browser-smoke-download-errors.json`）、最终 4 表格增量（历史证据：`artifacts/global-resume-optimizer-20261017/web-verification/browser-smoke-table-source.json`）。原 CSP 观察到既有 inline `script-src-elem` 拒绝；三阶段无新增 CSP 违规，不宣称基线 CSP 零违规。

## 命令与复现边界

证据 runner 使用原仓库 `.venv/bin/python`，产品与测试源位于 `/Users/liyulong/.codex/worktrees/global-resume-optimizer/offersteady`。Backend runner 清除供应商环境，只允许 loopback，PG 使用合成独立 schema 并清理。已执行的 Backend 新集/基线/适用集完整参数、返回码和 JUnit 在上述记录中；核心复现入口：

```bash
.venv/bin/python artifacts/global-resume-optimizer-20261017/backend-verification/run_checks.py new
.venv/bin/python artifacts/global-resume-optimizer-20261017/backend-verification/run_qualified.py
.venv/bin/python -m pytest -q scripts/release_support/global_resume_optimizer_20261017/test_release_controller.py
.venv/bin/python artifacts/global-resume-optimizer-20261017/probe-local-rehearsal/run_rehearsal.py
openspec validate add-global-resume-optimizer --strict
```

Web 已运行 `npm test -w @offersteady/web-global`、`npm run typecheck -w @offersteady/web-global`、`npm run test:copy -w @offersteady/web-global` 和生产构建；完整测试参数与产物清单位于 Web proof。公开构建配置以其中 `productionBuildManifest` 为准，不需要复制或输出私有生产环境。

## 尚待完成与限制

任务 1–4、5.1、5.2、5.4 为本地已完成；5.3 的最终文件冻结与实际镜像探针、6.1–6.5 的线上准备/重复门禁/发布/独立验收/交接仍未在本记录中确认完成。root 负责后续固定镜像与私有上下文；发布需等待真实面试、网页/桌面租约、音轨、回答/截图、资料任务、新简历任务和未知状态全部通过只读门禁，不清理或结束用户会话。安全漂移/归属未知停止自动切换，不能靠宽松回退覆盖后续变更。

所有输入为合成资料。未调用真实模型，未读取真实用户内容作为测试夹具，未做生产压力、实体设备或长期 P95 验收。模型语义质量、抗注入与语言实际成功率不能由离线 schema/事实守卫测试证明。独立执行器、全局单 claim 和既有面试回归已验；额外同进程隔离检查（历史证据：`artifacts/global-resume-optimizer-20261017/backend-verification/isolation-record.json`）实际占满 `LiveAnswerStreamExecutor`，同时运行 `ResumeOptimizerRuntime`：双方取消与容量分别释放、实时流可重连、优化仍全局单运行并且只结算成功次数；该 1 项为主套后的独立增量，生产源未变。此为有限合成行为检查，不承诺真实供应商容量或 P95 隔离。国服同步等待国际服用户验证后的另行授权。
