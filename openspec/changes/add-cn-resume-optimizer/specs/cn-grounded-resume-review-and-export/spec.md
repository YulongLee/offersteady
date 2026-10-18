## ADDED Requirements

### Requirement: Chinese evidence-based reference review
结果 SHALL 提供 0–100 参考总分/维度分、真实原文依据、中文解释/优先级建议/待补事实，明确不代表录用概率。服务器 SHALL 按版本权重计算总分，无 JD 时岗位匹配未评估。错误结构、分值、评估evidence引用、长度或语言 MUST 整体失败而非假成功；逐edit安全选择与无有效改写遵循本次11.x明确合同。

#### Scenario: Review with and without JD
- **WHEN** 有效结构化结果完成
- **THEN** 每个依赖来源的判断具有真实来源引用，中文说明明确，无 JD 不虚构岗位或把缺失项计零

#### Scenario: Invalid review
- **WHEN** 模型评估evidence返回虚假引用、越界分值、超限或不可解析结果
- **THEN** 任务失败并按原方式退还，原简历保留，无可下载的部分成功稿

### Requirement: Useful conservative Chinese rewriting
AI SHALL 允许有依据的中文词句改写，并从规范化原文的唯一 quote 构造局部替换，保留未编辑段落。数字/日期/联系方式/URL、机构学历、技术词、否定和责任程度 MUST 受事实守卫约束；JD 不能成为候选人事实，缺少成果/经历/技能 MUST 留待补充而不编造。Prompt/evals 和用户确认 SHALL 补足静态规则无法证明全部语义真实性的边界，不得逐字锁死全部中文造成仅排版的优化。

#### Scenario: Grounded Chinese wording improves
- **WHEN** 原文“负责使用Python开发数据接口”改为“使用Python实现数据接口开发”
- **THEN** 有依据的词句改写可通过，原有数字/技术/经历和未编辑内容保留

#### Scenario: Unsupported metrics or role upgrade
- **WHEN** 模型新增无依据指标、学历、机构、JD 技能或把参与改成主导/独立负责
- **THEN** 原守卫及评测拒绝该违规edit，不应用或保存其replacement；有其他合格修改可安全交付，无有效修改整体失败退款，不输出候选人已拥有该事实

#### Scenario: Prompt injection in source
- **WHEN** 简历/JD 含忽略规则、泄密或编造经历指令
- **THEN** 视作不可信资料，保持事实约束且不作为系统指令执行

### Requirement: Distinct editable draft and real downloads
UI SHALL 区分解析原文、AI 初稿和用户已保存稿，提供事实核实提示与 revision 安全编辑。已保存稿 SHALL 可下载真实 DOCX/PDF，采用同一中文可读标准模板，正确签名/MIME/附件名，支持中文/多页且完整不裁切，不加载远程资源。导出 MUST 认证、复核 owner/source/revision，并 private,no-store。

#### Scenario: Edit conflict
- **WHEN** 用户保存当前或过期 revision
- **THEN** 当前稿成功更新，过期请求冲突且不覆盖新稿；原简历/初稿保留

#### Scenario: Download Chinese multi-page documents
- **WHEN** owner 确认事实并下载当前已保存中文长稿的两种格式
- **THEN** DOCX/PDF 均为可打开的真实文件，内容一致、中文可读且分页无截断/重叠

#### Scenario: Unauthorized or unavailable export
- **WHEN** 未登录/他人请求、非完成任务、删除源或过期 revision 导出
- **THEN** 无正文/文件/私有对象地址返回，且不重新收费

### Requirement: Explicit independent save-as
用户 SHALL 显式确认将已保存完成稿另存为正常可选的新自有简历；同 job/revision 重放 MUST 返回同一资料，不覆盖原简历/旧会话快照。独立资料生成遵循既有准备流程，不另收优化费用。

#### Scenario: Save and reuse
- **WHEN** owner 确认另存当前稿
- **THEN** 新 document/version 独立且准备完成后可用于面试，原资料不变

#### Scenario: Replay and later task deletion
- **WHEN** 另存重放或之后删除优化任务
- **THEN** 不重复创建，新独立简历按自身删除规则保留

### Requirement: Simple focused resume optimization interface
页面 SHALL 以紧凑单列展示简历选择/上传、可选岗位和“开始优化”，历史通过独立入口访问。默认主操作视图 MUST NOT 常驻显示大块费用、积分余额、重置时刻或会员促销卡；JD和详细AI处理/保存说明 SHALL 可展开。处理同意仍须明确，积分创建仅在当次费用弹层确认后发出，所有原结果操作保留。

#### Scenario: A member starts a free optimization
- **WHEN** 有免费额度的会员打开页面并选择简历
- **THEN** 主视图直接呈现简洁表单和统一开始按钮，无费用权益大卡；明确处理同意后可免费创建，会员3次说明可在折叠帮助查看

#### Scenario: Optional details and history are accessible
- **WHEN** 用户需要JD、处理保存说明或历史记录
- **THEN** 可展开或切换查看，输入和当前稿状态保持，默认空历史不占据主要表单旁的大卡片

#### Scenario: Paid start requires an explicit contextual confirmation
- **WHEN** 非会员或免费3次已用完的会员点击开始
- **THEN** 先显示本次100积分/可用余额与确认或取消；取消不发创建，余额不足不扣费，报价变化后旧确认失效，不静默改扣

#### Scenario: Existing result tools remain available
- **WHEN** 用户打开已完成结果
- **THEN** 评分/建议/原文/编辑/保存/WordPDF/另存/删除均保留，其他工作台导航包括模拟面试保持

#### Scenario: Narrow display keeps the main action usable
- **WHEN** 页面在390像素或更宽屏幕打开
- **THEN** 简历选择、主按钮、可选展开、历史切换和费用确认均无横向裁切并可键盘操作

### Requirement: Strict model response transport normalization
国服 SHALL 仅在模型内容的传输层规范化开头UTF-8 BOM、外层空白或整体恰好一个完整json代码围栏；规范化后 MUST 为单一合法JSON对象，重复键、说明文字、多对象/围栏、非法或截断结果及非stop结束 MUST 失败。所有原有schema、原文依据、语言、数字/日期、联系方式、中文/英文事实和责任、非重叠改写及最终草稿守卫 MUST 保持，不得假成功或盲重试。

#### Scenario: A valid JSON review has only transport wrapping
- **WHEN** 合成有效结果仅附BOM/外层空白或整体单一json围栏
- **THEN** 去除包装后通过与裸JSON完全相同的结构和事实校验，参考分/优化稿一致

#### Scenario: Ambiguous or damaged model content
- **WHEN** 返回说明加JSON、多个对象/围栏、重复键、非法/截断内容、数组/标量或非stop结束
- **THEN** 固定失败，不提取子串或修补数据，无部分成功稿，并沿原方式退还

#### Scenario: Wrapped fabricated content remains invalid
- **WHEN** 包装内结果含虚假引用、新增数字/实体/技能、否定丢失、责任升级或重叠改写
- **THEN** 原事实守卫仍拒绝，包装兼容不得使不合格edit被应用；其余按11.x安全选择与零有效修改失败合同处理

### Requirement: Authorized bounded synthetic real-Provider validation
10.x已完成热修复的真实Provider验证 SHALL 与禁网候选探针分开，完整活动门禁通过后，仅直接Provider发送固定纯合成简历/JD，初次最多1请求、不创建任务/usage/账本、不访问钱包或真实用户资料。若固定原因失败，只可在批准四文件内按证据修正兼容/实现缺陷，补回归/eval并重冻结后对同一用例1次验证；仍失败或需范围外改变 MUST 停止自动发布并报告。全部事实/结构守卫和原预算保持，不盲重试，不输出原响应/密钥。此要求是10.x发布历史，11.x本地QA次数与边界由隔离能力的Three synthetic Provider QA cases remain bounded and isolated要求独立约束，不继承10.x发布动作。

#### Scenario: One synthetic Provider check gives a bounded release decision
- **WHEN** 经授权用纯合成用例检查实际Provider，返回成功或固定失败原因
- **THEN** 只保存安全结果/原因/时长，成功才进入发布验收；有据修正需新增合成回归/eval并最多同用例一次验证，不建真实任务或扣费，不能据此推断旧用户任务的精确原因或长期质量

### Requirement: Safe individual edit selection preserves strict global validation
11.x明确批准后，整个JSON/schema（含edit类型/字段/限长）、评分维度/分值、评估evidence/语言/JD及最终稿硬验证 SHALL 保持严格，任一全局错误 MUST 整体失败。每个合法结构edit SHALL 独立经过原逐字唯一quote、原全部事实守卫和原plain replacement格式校验；拒绝的edit及replacement MUST 不应用或进入review/草稿/诊断/日志。仅事实/格式合格且实质变化的候选之间判区间重叠，任何相交参与者 MUST 全部剔除；应用其余非重叠候选，不能先到先得。空白/标点/大小写/零宽格式变化只以casefold后Unicode isalnum串检测，不能用于事实或正文规范化。

#### Scenario: Valid edits survive independently rejected proposals
- **WHEN** 合成结果全局有效且同时提出安全edit和原事实/quote/格式守卫拒绝的edit
- **THEN** 只应用合格非重叠edit，拒绝replacement不持久化，安全初稿可completed且原费用一次settled；不能把某条守卫放宽来通过

#### Scenario: Global review errors still reject the whole result
- **WHEN** 任一JSON/schema/限长/评估依据/语言/评分/JD或最终稿全局硬限制无效，即使有安全edit
- **THEN** 整体失败、不交付部分稿，原路退还一次，不修补模型JSON或吞全局错误

#### Scenario: All overlapping qualified edits are excluded independent of order
- **WHEN** 合格实质候选彼此相交，含链式重叠或交换输入顺序
- **THEN** 全部相交参与者剔除，非相交候选仍保留，合并结果与输入顺序无关；相邻区间不算重叠

### Requirement: No effective edit fails with consistent original accounting
新任务 SHALL 至少应用一条合格实质修改且最终稿casefold+isalnum串不同于原文，才能completed。empty/all-noop/最终无实质变化 MUST 以invalid_output及draft/no_effective_edits失败，固定基句“本次未生成可安全应用的有效修改，原简历已保留。”；零applied但任何非noop拒绝 MUST 保留原输入首个非noop固定原因，alloverlap为edit_spans_overlap，不让noop遮盖事实错误。失败原finish/claim/revision/source/cancel屏障及同事务原路一次释放/退款 MUST 保持，不原文假成功，不额外收费。

#### Scenario: No effective edit fails and prioritizes a real rejection
- **WHEN** edits为空/全noop，或零applied并包含事实/quote/格式/overlap拒绝
- **THEN** 前者no_effective_edits，后者原顺序首个非noop固定原因；全overlap为edit_spans_overlap，均failed/released无部分review，重放不再扣退

#### Scenario: Meaning comparison cannot loosen fact checks or rewrite content
- **WHEN** 提议仅改变标点/空白/大小写/零宽格式，或试图以canonical化绕过数字/技术词/quote守卫
- **THEN** cosmetic不计实质改写，canonical只用于比较；事实仍按原字符串守卫，实际应用的replacement不被strip/修补，最终整稿无实质变化仍失败退款

### Requirement: Safe edit summary exposes counts and preserves historical results
新completed review SHALL 由服务端生成editSummary：proposedCount/appliedCount/retainedCount及retainedReasonCounts四组factCheck/sourceQuote/overlap/unchanged。各严格整数0..24，applied>=1、proposed=applied+retained、四组和=retained且互斥；不接收模型自报，不含拒绝正文/位置/内部诊断。retained指未采用提议数，不是未变区域数。历史无summary仍可读/编辑/导出。UI只展示严格合法completed摘要并标AI初稿，有未采用时“AI 初稿：已采用 N 项改写，M 项改写未采用，请核实。”，否则“AI 初稿：已采用 N 项改写。”；用户编辑不改该初稿计数，非法meta隐藏。

#### Scenario: Safe edit counts describe proposals without rejected content
- **WHEN** 部分或全部合格非重叠提议交付为completed
- **THEN** 服务端计数及互斥组关系准确，只含计数，不含被拒replacement/位置/reason；UI不虚称M处原文未变

#### Scenario: Old completed results and user revisions stay compatible
- **WHEN** 打开历史无summary结果或编辑已有新初稿
- **THEN** 历史正常使用，不回填/重收费，新summary仅说明initialDraft且不随用户编辑改数

#### Scenario: Malformed edit summary metadata is hidden instead of guessed
- **WHEN** completed meta有未知key、bool/非整型/越界、方程不符或applied为0，或任务未completed
- **THEN** UI隐藏该摘要，不猜测数字、不阻塞原结果或暴露内部对象

### Requirement: CN Prompt v2 aligns with each quote without loosening guards
保留v1并新增独立CN v2 Prompt及新任务版本元数据。v2 SHALL 明确每条sourceQuote自己的英文内容词原组合/数量保留，不从同段/别段/JD借词，不做中文到新英文缩写或格式近义替换；示例不变候选人事实。旧SAFE语法/保守动词及全部事实守卫 MUST 保持。模型无法安全edit可返回空数组，但新任务按无有效修改失败退款，应用不自动生成替代edit或重试。历史v1结果不改。

#### Scenario: CN v2 preserves content words inside each source quote
- **WHEN** 纯合成输入包含接口/API、SpringBoot/空格、REST API/复数、连字符或跨quote英文词风险
- **THEN** 新Prompt引导安全中文局部改写及原词保留，违规提议仍由原守卫独立拒绝；不推测用户实际新增词

#### Scenario: New v2 tasks do not rewrite historical v1 results
- **WHEN** 创建新任务或打开历史v1结果
- **THEN** 新任务标v2、历史版本/结果保持，空edit的新规则只在本次新实现执行路径生效，不回填旧记录

### Requirement: Allowlisted owner failure explanations appear in the compiled UI
Web SHALL 按errorCode精确匹配本地固定中文基句或其唯一退款后缀且allowanceStatus released，返回本地常量基句，不回显动态原串；新no_effective_edits加入invalid_output白名单。退款仍按权威状态独立显示。未知/私密/HTML/对象/拼接/状态不符 MUST 通用回退，原wire/权限/付费确认/主动重试保持，失败历史和轮询均真实可见。

#### Scenario: The compiled failed page shows an allowlisted local explanation
- **WHEN** 真实本地编译候选打开或轮询到已知code/固定基句的失败任务
- **THEN** 显示对应本地中文原因及独立退款，含无有效改写原因，不能只过wire测试或继续只按invalid_output通用回退

#### Scenario: Unknown private or inconsistent error messages stay generic
- **WHEN** 返回未知code、任意私密字符串/HTML/对象、前后拼接或退款状态不符
- **THEN** 固定通用说明且不显示原串/内部诊断，不重复退款声明，不自动重试
