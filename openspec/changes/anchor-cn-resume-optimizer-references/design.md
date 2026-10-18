## Context

[原CN合同](../add-cn-resume-optimizer/contract.md)、[失败诊断](../add-cn-resume-optimizer/failure-diagnostics.md)和[安全局部改写](../add-cn-resume-optimizer/safe-edit-application.md)已上线。现Provider v2让模型重写evidence.quote/sourceQuote，服务器用`quote in source`与`resume.count(quote)==1`定位；逐edit事实/plain/noop/全部相交剔除和零有效失败退款已建立。本轮只将新v3的定位转换为服务端唯一span，不能用模糊匹配修复模型引文，也不把旧用户失败归因于特定文句。

新鲜只读基线 `artifacts/cn-resume-optimizer-anchors-20261019/current-baseline.json` SHA `ae973bcfb50949682459afe2ca744bcc673b8727e201af9488d3de0b8a75df70`：实际Backend `2a907032…` / `sha256:6f9a55d8503971265e88dd97a8db804a0b3a7d8a785dc14320fc7fb54b3e443f`，全部231运行输入与CN工作区逐字一致，202完整schema/340Settings/315静态、7非目标及配置保持。主仓规范权威，CN工作区实现权威；本轮不是生产发布。

## Goals / Non-Goals

**Goals:** 让评分/建议和改写使用准确的当前原文片段；能区分重复文本，完整保留冻结输入及未改区域；保持原事实、权限、预算和金融行为；用多样合成材料和隔离PG/API检验，明确真实模型QA与本地替身测试的区别。

**Non-Goals:** 模糊quote搜索、模型offset/跨块range、全文重写、自动重试/换模型/增大预算、放宽事实、收费/DDL/配置/依赖变化、Web/UI/Global/助手/模拟面试或PDF/DOCX样式改动。没有生产切换/Git/真实用户材料读取/生产测试job、usage、钱包、资料写入授权。

## Decisions

### 1. 只对同一次冻结输入建立确定性连续片段

使用原任务payload已冻结的规范化`sourceText`与`jdText`，不再次走Parser、HTML转换、strip、Unicode/换行/空白归一化。Provider本次调用内分别生成`resumeFragments`和`jdFragments`；每个发送项只含`fragmentId,text`，不重复发送raw整稿。内部不可变表绑定精确原字符串及source，保存`start,end,text`的Python字符串半开区间；不得持久化新片段表、位置、拒绝edit或原模型响应。候选Prompt/QA输出也不含正文。

冻结分段算法：从start=0起，窗口end=min(start+600,len(source))；未到末尾时，在[start+200,end]范围优先选择最后一个换行后的边界，再选最后一个中英句终止符（`。！？.!?`）后的边界，再选最后空格/tab后的边界；该类没有则精确end硬切。分隔符属于原片段，不删空白、不跳块；到末尾保留全部剩余字符。LF与原CRLF/孤CR作为原字符保留，边界规则只取LF或不属于CRLF的孤CR，硬切仍不得修改任何字符。空JD生成空表；有效原来源准入沿用原逻辑。

每个source独立原序编号`r0001…`、`j0001…`；ID是位置标识，不包含用户标识/原文hash或语义判断。每片1..600字符，非末片至少200字符，原序join必须逐字符等于冻结source，片间相邻无重叠/空洞。40,000/12,000字符上限分别至多200/60片（总<=260），不因为大量短行新增更低准入。固定分段不理解姓名/公司/项目，不承诺每块都是语义句子；不支持模型自由缩小/扩展引用范围。

选择此规则是为了同时覆盖普通段落和长行，且保证输入膨胀有界；逐行无下界切分会使恶意换行产生数万编号。纯固定600可少一条边界规则，但普通行/句更易被拆开，因此在同一预算内优先现成边界。分段绝不能截掉尾部、合并归一文字或用模糊近似。

### 2. v3内部schema与public兼容

新增独立内部v3类型，不替换旧`ProviderResumeReview`/旧验证入口。形状仍有dimensions/suggestions/missingFacts/edits，原类型/字段集合/条数/分值/解释限长保持；v3 evidence只含`source:resume|jd,fragmentId`，v3 edit只含`fragmentId,replacement`，禁止模型quote/sourceQuote/offset/start/end/整稿/editSummary或其他额外字段。fragmentId为严格`[rj][0-9]{4}`字符串；字段类型/格式不合法仍为全局schema失败。

评分与建议每条ID在指定source的当前表必须存在且匹配前缀；任一未知/错源/伪造evidence全局按原`evidence_quote_missing`失败。roleMatch仍必须同时具备resume/JD依据，无JD不评此维度。服务器将有效ID逐条还原为原public `{source,quote:exactFragmentText}`，保留旧Evidence<=600、评分/中文解释/建议/缺失事实/JD规则。外部review不出现fragmentId、offset或新内部对象；原整体schema/语言/传输和最终draft验证保持。

### 3. edit按可信单span应用，事实选择算法保持

结构有效edit只从当前resume表解析一个ID。未知ID、JD ID、与当前表不匹配等语义引用错误按原`edit_quote_not_unique`固定原因、sourceQuote组独立拒绝；不能拿JD文字作候选人事实、不能读取其他调用表或任意寻找相同正文。合法ID唯一映射一个非空连续span，重复句可有相同text但不同可信offset；这等价升级旧count唯一定位，而不是取消唯一位置约束。

从旧`_validate_edit_span`中最小抽取纯事实/plain检查供两路径复用：legacy仍先原`count==1/index`，v3先可信ID/span，之后对该片段的exact原文与原replacement执行同一数字/日期/联系方式/URL、英文内容/数量、中英文机构学历技术、否定/责任及plain守卫，不借别块/JD事实，不strip后回写。原canonical只检测实质变化，不匹配或改写正文。

v3还必须保留原Markdown结构及行/格事实归属。每个候选先按可信span临时嵌回**完整原稿**，再以CRLF/LF/孤CR逐行对应比较有序结构，不能把600硬切产生的片段断头当行首：每行ending、原行首space/tab缩进和连续引用`>`、list marker（`-`/`+`/`*`或数字加`.`/`)`及其后space/tab）、heading marker（1..6个`#`后有space/tab）的原始前缀逐字保留；heading整行原文不改。原空白行完整保持。表格分隔行（含pipe且各非空cell去边缘space/tab后均为可选冒号+至少3个`-`+可选冒号）与horizontal-rule（去space/tab后由同一`-`/`*`/`_`至少3个构成）整行保持，不把不可编辑markup变正文。

任一含literal pipe的对应原行按pipe切成有序cell；要求该行pipe数量、首尾pipe形态及每格原边缘space/tab完全保持，原空白cell完整保留，不允许增删行列或重新分组。允许非空cell内安全措辞优化，不整表readonly。对临时嵌回后每个发生变化的对应**完整原行/新行**复用同一原事实/plain守卫；表格还对每个变化的对应**原cell/新cell**分别复用，禁止利用200–600字符块的整体词数相同，将技术/数字/技能/成果从别行或别格搬过来。原行/格为空白时不调用strip后的事实比较放行，而是保守原样保留；不新增Markdown解析依赖或推测表格语义。结构不符用原`draft_invalid`/factCheck，行/格事实失败保留原事实固定原因/factCheck。

合法实质候选仍按原全部相交参与者剔除规则处理。重复同一ID的合格实质提议必然同span，全部overlap剔除；不能先到先得或最后覆盖。已被事实/格式/结构/行格归属拒绝和noop仍按原先顺序不进入合格冲突集。按受信offset逆序构建稿，所有未修改区间原字符完全保留；合并后再执行完整原稿→最终稿的原事实检查、有序结构与逐行/逐格复核及原draft硬验证，不能让多个独立候选合并绕过。summary计数、零有效首个非noop原因与原路一次退款不变。ID不代表建议真实，不能省略事实核实。

### 4. Prompt版本和有界资源

新增`ai/prompts/resume-optimizer/review.zh-CN.v3.md`，新任务版本`resume-optimizer-zh-CN-v3`；SCORE_VERSION保持。v3只接收一次编号视图和targetRole，明确来源不可信、只引用给定ID、整块replacement必须保留块内全部事实/未需修改内容、原行/表格单元事实归属与Markdown前缀/标题/空白/分隔不变，跨行/格/块借词和缩写仍禁止。保留v1/v2文件与行为，不能在v3不合格时回退接受旧quote格式。

root已确认最小版本兼容：Provider.generate新增可选`prompt_version`，直接调用默认v3；Runtime只从重新授权fresh payload显式传promptVersion，新create记v3；旧v1/v2执行各原Prompt/legacy schema和count守卫。未知/缺失版本在外发前按既有`runtime_internal_error`固定诊断fail closed，不透传版本值、不默认为v3，不改旧completed/meta。仅允许service `_execute`这一可信版本参数增量及必要stub签名适配；创建沿用已导入常量，无其它service行为变化。

原source40000/JD12000/targetRole120/draft60000、最多24edits、90秒/6500输出tokens/256KiB响应流限长、全局8unfinished/1Provider与原连接限制全部保持。编号视图只序列化一次，文本各字符恰好一次；与原相同JSON编码的resume/jd/targetRole载荷相比，结构额外UTF-8字节上界32KiB作为实现/回归不变量，不增加模型预算、不额外降低用户准入或静默截断。最大长度、全短行、空白、转义和Unicode输入均须证明此上界；不满足是实现失败，不能转成自动删内容或模型重试。

### 5. 验证和可选有界真实质量QA

纯合成回归/eval覆盖常见中文技术、校园/有经验/非技术/中英混合、重复句不同位置、CRLF/tab/空行/Unicode、超长单行及52k总输入；引用伪造/错源/offset/额外字段/注入、事实与全局错误、重复合格ID全部剔除、partial/zero/noop/原summary及传输/BOM/围栏边界。另覆盖块断头/CRLF中间硬切、标题/list/quote/table分隔/缩进/空白及管道形态，保持整块总词数却跨行/格搬技术/数字/技能的恶意结果和正常单格措辞；最终合并仍复核。旧Provider/Global共享helper/PDF全部基线回归保持，隔离真实PG/API验证partial一次settled、零有效一次released、重放/取消/源删/旧claim/revision及public no-store/无内部字段。

可选真实QA不是本地假Provider测试：最多6个预先冻结独立纯合成样本，每例至多1次，总实际请求<=6；v3 candidate/全输入/Prompt/script/case及单次marker必须绑定，先完成候选禁网只读无lifespan/七副作用0及版本/真实导出保留探针。root另行审核质量阶段授权/私有配置隔离并明确QA GO；每例前用当前实际旧Backend固定digest执行原完整七门禁且全有效空闲，忙碌停止/延期，未知或失败停止报告。

QA仅隔离进程直接调用固定Provider，不建生产job/usage/账本/钱包/资料、不读真实用户/OSS；私有配置留服务器、不输出原响应/Prompt/正文/密钥。调用前持久O_EXCL marker绑定固定版本/case，先消费再外发；超时/不确定请求是否发生按已消费处理。任一不合格或异常停止剩余用例，不自动重试、修后重跑、换模型、扩大预算或用新目录绕过marker；如需新增调用必须另有明确授权。只留安全成功/固定失败原因、计数/时长和请求数，6例不能证明长期质量或旧用户问题已解决。

## Risks / Trade-offs

- [600字符片段可能大于原自由短quote] → Prompt要求整块保留事实和未改内容，测试多种长度；只承诺定位稳定，不保证每份简历都有可安全实质改写。事实静态规则不能证明全部中文语义，用户事实确认保持。
- [相同文本的多个位置不再被count一律拒绝] → 仅当前服务端不可变表的唯一span可应用；不同ID不同offset、同ID合格提议全冲突，并保留原所有事实守卫。
- [引用ID正确但模型建议失实] → ID只证明来源位置，全局/逐edit事实规则和Prompt/evals仍独立生效；不把ID当事实真实性证明。
- [一个块跨多行/多格，整体词数掩盖事实搬运] → 在完整原稿嵌回后按对应行/cell复用原事实守卫并保留有序结构，最终合并再次核对；静态规则仍不能证明所有中文语义，不能宣称绝对无事实风险。
- [输入编号/JSON有额外开销] → 最多260片与32KiB结构开销不变量，保留原输入准入与90秒/6500等设置，不增加调用数。
- [未知版本、旧queued或迟到执行] → fresh payload显式版本、legacy保留、未知fail closed；原claim/source/revision/取消退款事务不动。

## Migration Plan

本轮按新鲜231基线完成本地实现/隔离测试/证据；无迁移、旧结果回填或生产开关变化。root读完整context、双strict并记录实施GO后才写产品。可选QA只在独立GO后进行，不能混同生产发布。后续用户另行授权部署时，须重新按实际镜像/完整源/路由/配置/静态/非目标及活动门禁拟定发布规范；不沿用本轮GO自动切换。

## Open Questions

无阻塞产品问题：用户已授权本地开发，自测和非目标明确。可选6例真实QA是否执行、精确case/script/candidate冻结和QA GO由root后续证据审查决定；未执行须记录未执行，不预标质量通过。
