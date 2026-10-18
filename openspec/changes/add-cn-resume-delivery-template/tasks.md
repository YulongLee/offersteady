## 1. 规范与基线

- [x] 1.1 root 复核用户本地授权、本规范/非目标/场景、实际国服 Backend/Web 快照及完整 230 输入绑定；严格校验通过后记录本地实施 GO，主仓与国服工作区规范一致。

## 2. 专业 PDF 增量

- [x] 2.1 实现 CN 专用保守有序文档模型与 PDF renderer，涵盖标题/联系/精确栏目/明确经历/列表、未知完整正文、真实内嵌文字、长行/分页、原字形/输入限制及有界 lazy 渲染；不得改共享 helper、事实或原顺序。
- [x] 2.2 在 CN service 仅默认 PDF 路径 lazy 接入新 renderer，保留 injected exporter、DOCX 原调用、两次 owner/source/completed/revision 复核、factsConfirmed、安全错误及无收费语义；页面只增加简短 PDF 模板说明。

## 3. 本地回归与视觉验收

- [x] 3.1 新增能复现原排版问题的纯合成回归：常见/歧义结构、全部事实/地址/顺序、中文混合语言、长 URL/多页/页末标题/长段落、非法/缺字、lazy/锁并发失败恢复；保留原 DOCX/Global 与 CN 权限/删除/更新/revision/免费导出测试。
- [x] 3.2 生成 experienced/campus 两份真实新模板 PDF 和边界样例，检查签名/MIME/A4/内嵌字体/全文顺序/无动作资源，渲染全部页面并由 root 逐页检查无越界、重叠、截断、孤立标题/空白尾页；记录真实页数、耗时与限制。
- [x] 3.3 提供本地可打开 PDF/逐页图与 test-only 真实文件下载预览；检查生产 build 排除样例资产/生成器，执行相关 Web 检查（若修改）、完整源/费用/Prompt/共享 helper/模拟面试保留审查。

## 4. 交付

- [x] 4.1 逐场景填入 verification 的实际证据，记录未部署、无生产写入/真实用户数据/模型/Git及未覆盖限制；双工作区 OpenSpec strict 和 Markdown 链接校验通过后交付本地样例，等待用户后续晚上发布授权。

1.1 root local implementation GO: 2026-10-18 root read all apply context, both strict checks passed/state ready, user explicitly authorized local development and self-test only. Fresh actual runtime SHA39ee2323bf893db536bd677bf949be9781e0961bfbbd25d9fba9c1cf28a1be68 binds f6/2124 and all230 runtime inputs byte-identical to the CN worktree. Approve CN-only PDF renderer/service dispatch, minimal UI note and isolated local synthetic renderer/preview; preserve DOCX/shared helper, Prompt/facts/fees/revision/source barriers and all other features. No production writes/deployment/model/Git in this turn.

Root narrow formatting GO: reviewed D3/D4 and design clarification, strict passed. Support a short original first-line document header only with explicit email/phone in the next at most3 nonblank header lines. No identity field, invented text, reordering, URL/date/id evidence or new model call; retain unsupported inputs as body. Add positive/negative regression before final freeze.

Root final local acceptance: final renderer 6d466a27fef9bc5454420e00913c8bbb3275b6264cabc80e370de446ccb3d7db, Backend154/Web586, real synthetic HTTP20, 7PDF/11pages individually visually approved; both strict commands exit0 and both Markdown link checks pass. Local preview and synthetic PDFs delivered for review; no production deployment/model/Git authorization or action. Evidence: final-validation.json and verification.md.

## 5. 商务深蓝外观追加（仅本地，首轮7/7历史保持）

- [x] 5.1 root复核用户最新视觉授权、受控深蓝规范与冻结色值/尺寸/字号；绑定已验收6d基线与所有非目标，双根strict通过后记录本轮局部实施GO。
- [x] 5.2 仅CN renderer实现冻结的抬头/深蓝强调、淡底/左色条、经历层级与留白等局部视觉；保留原解析/事实/顺序/真实文本、标点内缩/自然分页/有界锁与全部非目标，不改Web/Global/DOCX/生成或依赖。
- [x] 5.3 新增D13颜色/装饰/高对比/内容顺序回归，运行受影响PDF/原导出与CN保护回归，重新生成两用户样例及全部边界PDF/逐页图，实际检查全文/字体/A4/坐标/装饰边界与全部页面视觉，至少两用户样例灰度可读；记录新SHA/真实计数而不复用旧验收。
- [x] 5.4 追加新版D13及D1–12相关复核证据、本地样例/下载核验与已知限制，保留原7/7及失败历史；双根strict/链接和非目标审查通过后本地交付，不进行生产/模型/Git。

5.x状态：四项本地视觉任务完成，当前总11/11；首轮7/7及失败历史仍保留。最终769源码、170项回归、14彩页/2灰度逐页视觉、6项本机HTTP和非目标保留均有本轮证据，双根strict/链接收尾见business/final-validation.json。未部署、未调用真实模型或操作Git。

Root5.x local GO: latest user asks a more polished standard template; root read all apply context/deltas and froze navy header/section/typography rules with conservative measured fallback. Both independent strict checks exit0; existing6d local input manifest matches all9 sources. Approve only CN renderer visual implementation and pure regression/synthetic PDF QA under design/D13. No production/Web/service/Global/DOCX/Prompt/fee/dependency/Git/model changes authorized.


## 6. 用户授权的国服生产增量（本地11/11历史保持）

- [x] 6.1 root核对已取得007c9fdd…新鲜实际CN Backend及Web第7非目标完整基线、两源allowlist/AST和本地最终证据SHA，确认Backend-only范围；双根strict与完整context复核后记录本轮生产实施GO，不预标发布完成。
- [x] 6.2 准备专属已审控制器/计划/支持SHA与固定父digest两源候选，完成七门禁/TCP-netns前后身份/仅恢复stoppedProcessProof全条件/归属/失败恢复/无重复切换工具回归，以及实际禁网PDF/原DOCX/全文字号/完整schema/Settings与副作用0探针；独立绑定候选digest。
- [x] 6.3 按同锁新鲜完整七门禁分别preflight与切换前复核，加临近实际TCP/netns身份绑定（仅严格恢复exited candidate可停态证明），只在有效空闲时切CN Backend固定digest；忙碌defer、unknown/readfail/drift停止，必要恢复也重复相同保护/归属并保留用户数据，所有分支按实际记录。
- [x] 6.4 独立verify实际固定目标冷启动/健康/重启/完整源/schema/Settings/有效配置、Web静态/NGINX/全部非目标及公共/匿名守卫，再做真实短窗口脱敏错误统计；不得登录真实用户或产生生产测试写入/模型调用。
- [x] 6.5 更新实际生产记录与D14–20/任务结果和限制，保留11/11本地及旧失败证据，双根strict/链接收尾后通知用户正常账号测试；无Git/Global/助手/费用或其它组件扩展。

6.x状态：6.1–6.5已完成，当前总16/16（本地历史11/11保持）；final-2修复冻结/96项工具与实际6f9候选10PDF14页/原Word/七类副作用0均通过。preflight与deploy临近完整七门禁各有效空闲、TCP0/netns绑定，实际只切CN Backend为2a907032…/6f9a55d8…，上海2026-10-19 00:52:37启动；deploy/verify各9项公共/匿名检查及完整231源/202schema/340Settings/315静态/7非目标保持通过。初始53.214秒134行与最终180秒406行均无截断，healthy/restart0，错误统计均0；signature里的starting是切换瞬间历史。实际无busy/恢复/失败/代理reload。独立最终上线审查7b98961d…已通过，6.5的双根strict/链接与记录收尾已通过，最终结果见发布证据final-validation.json；工具/视觉失败历史保留。具体合同见production-release.md。

Root6.1 production implementation GO: latest user explicitly authorizes CN deployment. Root read complete apply context and current production contract, fresh read-only007c9fddb42158eb214be28ceac2e2922a89552d38ad67a44c9d0c606d4c63b5 baseline and exact tested two-source delta; both strict commands exit0. Admit Backend-only two-source immutable-parent candidate/controller preparation, actual offline synthetic proof, protected seven gates plus actual-netns TCP and narrow owned stopped-process recovery proof, and only guarded single-component deployment after tooling/candidate review. This is not a claim that candidate or deployment has passed. No Web rebuild/Global/companion/fees/config/deps/real model/user resume/Git actions.
