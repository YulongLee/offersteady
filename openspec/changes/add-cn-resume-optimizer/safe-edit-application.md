# 国服安全局部改写与失败说明合同（11.x本地开发）

状态：root已完成11.1独立strict及明确本地实施GO，11.x本地开发与验收进行中，逐项实际状态见[tasks](tasks.md)。用户已明确要求按已讨论的优化点开发；此前仅研究的11.x已升级为本地开发、自测及本地预览范围。11.2–11.4已据本地证据完成，真实compiled浏览器与隔离QA仍按实际结果单独验收，不提前勾选。本轮不执行生产切换、Git、Global/助手/Admin或收费/DDL/环境变更；历史41项完成事实和原生产/失败记录保持。此前[研究草案](english-token-and-error-display-research.md)关于“不得筛选edit”和“空edits可交付收费”的限制由本次明确批准的安全选择/无有效修改失败规则取代，不静默回写历史行为。

## 1. 冻结基线与目标

root已只读确认当时实际Backend b955c33e…/6f2a53f5…、Web029e84e0…/20d6a03a…：229完整源与CN工作区逐字一致，202条完整OpenAPI/schema、340个Settings、305项静态及NGINX相同。安全证据为原仓库`artifacts/cn-resume-optimizer-safe-edits-20261018/current-baseline.json`，SHA-256 `08a10e801e42dae7479c8d21750723161ffd9d697875547ad11a7738fe738808`。11.1已按随后记录的root实施GO完成；后续来源变动必须重核对，不用旧目录或健康版本替代真实组件。

本轮开发在原功能上增加：逐edit安全选择、无有效改写失败退款、中文Prompt v2和固定安全错误实际显示，以及AI初稿计数摘要。原普通/模拟/笔试、资料、钱包、会员3次/其他100积分及明确付费确认、claim/revision/source/cancel/ledger守卫保持。真实新失败已知facts/fact_english_content_added和全退，但不知道新增的具体词；不得读取用户正文/原模型输出作为夹具，不能断言是API或某个技术词，更不能写成已修复原任务。

## 2. 全局验证仍是不可降级门槛

原JSON解析/限长、完整schema（含每个edit的类型/字段/长度）、评分维度集合/分值、评估维度和建议的原文evidence、中文解释/待补事实、JD规则、整个结果和最终稿的原硬边界保持。任一全局错误必须整体失败，没有部分交付。模型不能提供editSummary；它只由服务端在合法结果上计算。不得从说明中抽取或修补JSON，不重试模型、不吞掉整体错误。

## 3. 确定的逐edit安全选择顺序

对schema有效的最多24个提议按原输入顺序独立检查，原文保持同一规范化输入副本，不修改原存储：

1. 使用原逐字且唯一的sourceQuote守卫；不存在/重复引用的提议不应用，分组sourceQuote，固定原因沿用edit_quote_not_unique。
2. 使用原数字/日期/联系方式/URL、英文内容词保留、中英文实体/学历/技术、否定/责任等事实守卫；同时以原validate_plain_text独立校验replacement格式，HTML/control/纯空白等无效格式拒绝。检查不把strip后的值写回，实际应用仍用原replacement字节。此类提议不应用，分组factCheck，保留原固定原因；plain拒绝为draft_invalid。
3. 对通过事实/格式检查的提议，只用 `''.join(c for c in text.casefold() if c.isalnum())` 比较quote和replacement是否有实质字符变化。相同的提议不应用，分组unchanged。空白/标点/大小写/零宽格式变化本身不算有效；此canonical只作变化检测，绝不能用来匹配quote、放宽事实检查或改写实际正文。
4. 仅在上述事实/格式合格且有实质变化的候选集合中计算原文半开区间。任何两个区间相交的所有参与者全部剔除，分组overlap、固定原因edit_spans_overlap；相邻区间不算重叠。不能按“先到先得”保留一个；链式A交B、B交C时A/B/C全剔除，结果不依赖输入顺序。已拒绝提议不参与这一合格候选冲突图。
5. 按原文位置应用其余全部非重叠合格提议，保留未由这些合格提议修改的内容，再运行原最终draft硬验证。无效edit对象及其replacement不进入review、草稿、诊断或日志，不存拒绝片段/位置；也不新增模型原始输出存储。

## 4. 零有效改写不能假成功

完整AI初稿必须至少应用1条合格的实质修改，且最终稿的上述canonical与原文不同。只有empty edits、all-noop或最终整稿无实质变化时使用新的固定diagnostic `{stage:"draft",reason:"no_effective_edits"}`，公共errorCode仍invalid_output。固定中文基句为“本次未生成可安全应用的有效修改，原简历已保留。”；退款后缀仍只由已提交released状态追加。

若appliedCount=0且包含任何非noop拒绝，必须保留原输入顺序中首个非noop固定原因，不让noop掩盖事实错误；全overlap返回edit_spans_overlap。不能把全不合格提议替换成原文/空edits而标完成。最后整稿违反原硬限制仍按该固定错误失败，不降级交付。失败无review/部分稿，沿原同事务finish原路释放一次免费次数或退款100积分；partial成功则一次completed/settled，不二次扣费，编辑/下载/另存不额外收费。

## 5. 公开安全计数与旧结果兼容

新成功review增加服务端生成的可选字段：

```json
{"editSummary":{"proposedCount":4,"appliedCount":1,"retainedCount":3,"retainedReasonCounts":{"factCheck":1,"sourceQuote":0,"overlap":2,"unchanged":0}}}
```

所有值必须是严格整数0..24（拒绝bool/float/string），四组互斥。`proposedCount=appliedCount+retainedCount`，四个reasonCounts之和等于retainedCount；新completed必须appliedCount>=1。失败不交付review/summary。summary不包含被拒正文、replacement、位置、原始内部诊断或用户标识。retainedCount表示“未采用的提议数”，不是“不变位置/段落数”：坏提议可能覆盖另一合格提议的源区域，不能声称有M处原文完全未变。

历史已完成结果无editSummary保持可读/下载/编辑；不回填旧记录。页面仅对completed且严格完整校验通过的元数据显示：有retained时“AI 初稿：已采用 N 项改写，M 项改写未采用，请核实。”；没有时“AI 初稿：已采用 N 项改写。”。它只描述initialDraft，不随用户编辑改数字。字段缺失/未知/类型/计数关系不合法时隐藏摘要，不猜测、不阻塞旧结果或把内部数据输出。

## 6. Prompt v2和固定安全错误显示

保留v1，新增独立`ai/prompts/resume-optimizer/review.zh-CN.v2.md`；新任务版本为resume-optimizer-zh-CN-v2，历史v1不改。v2明确每条sourceQuote自己的英文技术/内容词按原组合/数量保留，不从同段、其他项目或JD借词，不做中文接口→新增API、SpringBoot→Spring Boot、REST API→REST APIs等格式近义变化；例子仅是规则示范，绝非候选人事实。旧SAFE词、schema和事实规则不放宽，模型预算/超时/并发不改。无法安全提供edit可让模型返回空数组，但按本合同整体无有效改写时失败退款，不收费交付原文。

Web最小固定helper按errorCode及已审核中文基句白名单匹配既有errorMessage，或基句+唯一固定退款后缀且allowanceStatus为released；返回本地常量基句，不直接回显动态服务端原串。新no_effective_edits基句加入invalid_output白名单，退款继续由原权威状态段独立展示。未知code、私密/HTML/对象/前后拼接、退款状态不符通用回退。失败历史与异步轮询都实际可见安全原因，原权限、重试/付费确认和private,no-store保持。

## 7. 验证分工和本地边界

新增合成Provider/AI eval覆盖mix安全与违规、全局错误、全部重叠参与者、输入顺序、empty/noop/最终无变化和首个非noop原因；root负责独立本地真实PG/API partial completed/settled、零有效failed/released、同事务退款/重放、claim/source/cancel竞态和wire；保留原金融/旧功能回归。Web验证固定消息/摘要正反、历史旧结果、用户编辑和真实组件；实际本地编译/静态组装Chrome及原导航必须检查，不只测API wire。所有样本纯合成。

本轮交付本地可审查版本与本地预览，暂不执行生产Backend/Web切换、不写新生产job/账本/资料，不Git/Global/助手/Admin。实际Web编译候选须从已冻结镜像增量保留全部305旧静态/正文/CSS/NGINX和普通/模拟/笔试，不用完整dist覆盖真实基线。后续上线另按当时真实组件重新冻结、七完整活动/金融/CN优化门禁、完整挂载/非目标签名及固定归属回退；当前不把候选准备或本地测试写成已上线。

## 8. 有界纯合成真实Provider QA

本轮明确GO后，可在服务器私有配置仅留服务器的前提下，用候选隔离进程直接Provider验证最多3个固定、独立约3千字符技术Markdown合成用例，各至多1次。候选须先通过禁网只读/无生命周期副作用探针；每次调用前完整七门禁可用且无受保护工作，先消费与candidate/Prompt/script/case绑定的单次marker。仅输出固定结果/原因/计数/时长及是否有真实合规改写等安全摘要，不输出原响应/Prompt/配置/密钥，不读用户资料、OSS或真实任务，不碰钱包/创建生产job。

检查必须确能产生合规局部修改和正确计数，而非空edits/原文假成功。任一失败停下报告，不自动重试或追加；有据修正需更新合成评测/回归/候选并由root重审，不能靠重复采样碰运气。3次QA成功不代表原用户任务已成功或长期模型质量验证，不等于已授权生产切换。

## 9. QA预启动挂载故障的窄修正（不改变产品或模型预算）

首轮QA目录`/opt/offersteady/qa/20261018-cn-resume-safe-edits-1`的实际candidate912137e9…已通过230源/202完整路径/schema/340Settings、真实导出及七类副作用0的禁网只读探针。case1在完整七门禁空闲后，Docker因只读父目录上不存在的嵌套`/verify/case.json`挂载点于runc容器init阶段失败。安全分类证据`artifacts/cn-resume-optimizer-safe-edits-20261018/qa/first-attempt-safe-diagnosis.json`确认容器进程未启动、Provider请求0，后例未开始，未切换生产或导出原stderr；旧consumed marker、控制器、prepared包及失败证据保持，不原地清除或重跑。

这是已批准隔离QA的测试工具缺陷修复，不重新批准产品变化或上线。新目录`/opt/offersteady/qa/20261018-cn-resume-safe-edits-2`须重新冻结控制器/plan/tag/输入SHA，在同一QA排他锁内将当前纯合成case原字节写入现有目录的`case.json`、模式0600且核对case SHA；容器只保留一个整个QA目录的只读挂载，不再嵌套绑定不存在目标。保留candidate/source/Prompt/case绑定、禁网只读无生命周期探针、七完整门禁、持久O_EXCL marker及固定安全摘要；不更改产品源/配置/金融/事实守卫，不接触真实用户内容。

必须补充同样命令形状的实际Linux Docker禁网只读挂载演练及合成回归，验证容器可读取已存在的0600合成case、只有单一目录只读挂载，旧失败仍不能重复。只有上述安全证据明确证明旧容器进程与模型均未开始、root重审GO后，新目录才可恢复原三例各最多1次的计划；本轮总实际Provider请求仍不超过3。若旧调用可能已开始、请求状态未知、没有可靠启动前证明或新尝试仍失败，停止并报告，不以新目录换取模型重试或重复采样。首轮停止时真实模型尚未通过，11.6/C73和新工具场景当时保持待验收；忙碌或门禁未知即停止，本地可测版本照实交付，不自动等待切换。

当前最终状态：dir2已通过实际Linux禁网单挂载演练和完整230源/202schema/340Settings/真实导出/七副作用0候选探针，三合成例分别19.693/21.130/22.835秒、有效5/7/5项（第二例2项unchanged未采用），各1请求共3；final verify及独立审核通过，旧dir1进程未启动/0请求和consumed marker仍保留。393不同Backend/572Web、42新AI eval/22真实PG/API、13实际compiled IAB/Chrome观察点通过。root完成47/47本地任务和75场景，当前没有本轮生产切换/Git或真实用户任务重放。详见[本地交付记录](../../../docs/releases/cn-resume-optimizer-local-20261018.4.md)。
