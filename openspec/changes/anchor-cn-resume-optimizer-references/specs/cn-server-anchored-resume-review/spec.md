## ADDED Requirements

### Requirement: Deterministic source fragments preserve the entire frozen input
CN v3 SHALL 从同次任务已冻结的规范化resume/JD构建服务端原序连续片段和可信半开位置表，使用[设计](../../design.md)冻结的600/200边界规则、source独立r/j编号。每个字符 MUST 恰好出现一次，join与原字符串完全相同，不strip、归一化、丢弃空白/尾部或接受模型offset。ID SHALL 只定位当前source唯一span，不是事实真实性证明，不新增持久化片段数据。

#### Scenario: A1 Identical frozen inputs produce identical complete partitions
- **WHEN** 同一纯合成resume/JD重复建立表，或输入含标题、短行、长句和超长单行
- **THEN** ID/区间/text完全确定，单片1..600字符，非末片>=200，区间连续无洞/无重叠，原序join逐字符等于完整原文

#### Scenario: A2 Repeated text retains separate trusted positions
- **WHEN** 两个不同位置出现逐字相同片段，模型选择其中一个已提供ID
- **THEN** 只解析该ID对应当前source的唯一位置，不用全文count重新歧义拒绝、不影响另一个未编辑位置，也不跨请求复用表

#### Scenario: A3 Whitespace and Unicode survive without normalization
- **WHEN** 原文含CRLF、孤CR、LF、tab、空行、组合字符、中英符号和尾部内容
- **THEN** 分段/映射不改变任何字符；全部未编辑位置和分隔符在重建稿中原样保持，不用模糊空白匹配

### Requirement: Anchoring respects existing admission and model budgets
原resume40000/JD12000/targetRole120/draft60000、24edits、90秒/6500输出tokens/256KiB响应上限及8unfinished/1Provider MUST 保持。v3输入 SHALL 只发送一次带ID文本视图，不重复raw全文；最大输入总片数<=260，结构序列化额外字节 SHALL 在设计32KiB上界内，不静默截断或用更低准入掩盖膨胀。

#### Scenario: A4 Maximum and adversarial line structure remain bounded
- **WHEN** 原合法输入达到40000/12000上限或含大量单字短行、转义字符/Unicode
- **THEN** 完整文本仍被保留，片数/结构字节上界成立，原输入仍可准入，调用预算/并发不变，无自动重试

### Requirement: V3 evidence is strictly resolved and converted to the existing public review
内部v3 evidence SHALL 只接收source/fragmentId，edit只接收fragmentId/replacement，额外quote/offset/整稿/summary字段 MUST schema失败。所有dimension/suggestion依据ID MUST 在当前指定source存在；错误依据为全局失败。合法ID SHALL 由server取exact原text还原旧public `{source,quote}`，旧维度/分数/中文/JD/限长/严格传输与review形状保持，public不暴露ID/offset/内部表。

#### Scenario: A5 A fabricated or wrong-source evidence fails the whole review
- **WHEN** 任一dimension/suggestion引用未知ID、resume与JD错源或伪造格式/模型offset
- **THEN** 原结构或固定依据错误整体失败，无partial稿；不搜索近似原文、不接受模型自报位置或从别source借证据

#### Scenario: A6 Valid references reconstruct exact public quotes
- **WHEN** 评分和建议引用有效ID，含有JD时的roleMatch
- **THEN** 每条public quote均为服务端原片段逐字文本且<=600，roleMatch保持双来源，其余评分/中文/缺失事实规则不变，无ID/offset进入公共结果

### Requirement: Trusted edit positions preserve all original safety selection rules
结构有效v3 edit SHALL 只解析当前resume表单一可信span，未知/JD ID按旧sourceQuote组及固定原因拒绝；合法定位后 MUST 原样复用全部原事实/plain/canonical/重叠/最终稿守卫。v3 SHALL 按[设计](../../design.md)将每候选嵌回完整原稿比较有序Markdown结构，并对每条变化的对应完整行/表格对应cell分别复用原事实守卫；原空白行/cell、heading及分隔行保持，不能跨行/格搬事实。所有合格实质相交参与者 SHALL 全部剔除；按可信offset应用其余，最终合并再次复核整体事实/有序结构/对应行格及原draft，原summary和首个非noop错误选择不变。不允许模型quote、offset、跨块range或全文重写代替安全定位。

#### Scenario: A7 A valid ID cannot bypass factual checks
- **WHEN** ID正确但replacement新增数字/日期/联系方式/URL、英文技术、机构学历/责任/否定/中文技能或非法plain内容
- **THEN** 与旧逐字quote路径相同事实拒绝，不借其他块/JD事实、不strip后回写；有其它安全edit时partial，否则原规则失败

#### Scenario: A8 Duplicate qualified IDs are all excluded as overlapping
- **WHEN** 多个合法实质edit引用同一ID，或交换它们的提议顺序
- **THEN** 这些同span合格提议全部overlap剔除，不先到先得；事实拒绝/noop仍按原顺序不进入合格冲突集，其余不相交edit正常应用

#### Scenario: A9 Invalid edit references preserve partial and zero-effective semantics
- **WHEN** 结构有效edit包含未知或JD ID，另有安全修改或全部没有安全修改
- **THEN** 错误ID只按sourceQuote拒绝组计数、固定edit_quote_not_unique，前者可一次安全completed/settled，后者按原首个非noop原因failed/released，拒绝正文/位置不保存

#### Scenario: A16 Source Markdown survives replacements at arbitrary fragment boundaries
- **WHEN** 一个可信片段跨标题/list/quote/table或从行首前缀、CRLF中间开始，replacement试图改换行/缩进/标题/列表符/引用前缀、表分隔/横线/pipe数或cell边缘空白
- **THEN** 在完整原稿嵌回后按有序行结构拒绝该edit为draft_invalid/factCheck，不将片段断头误作行首；原空白行/cell和不可编辑markup保持，正常同格安全措辞仍可通过

#### Scenario: A17 Block-wide counts cannot move facts between lines or cells
- **WHEN** replacement保持整块数字/英文技术/中文技能等总数，却将其从一条原行/原cell转移到另行/另cell，或多个独立候选合并才产生归属/结构问题
- **THEN** 对应变化原行及表格cell的原事实守卫独立拒绝，最终合并整体/结构/行格复核再阻止交付；不借其他行/格事实，不放宽旧事实规则，不声称能证明全部中文语义

### Requirement: Existing financial and user-data barriers stay authoritative
原公共API、会员每日3次/其余100积分、幂等/owner/source/claim/revision/取消/删除、partial/zero/noop及退款事务 MUST 保持。定位升级不得重扣/重退、复活迟到结果、改变用户已保存稿/旧初稿或下载。失败无partial review，权限及private,no-store保持。

#### Scenario: A10 Global validation and no-effective edits still fail safely
- **WHEN** 全局schema/语言/评分/JD/依据或最终稿错误，或无合格实质修改
- **THEN** 原整体失败/无有效修改固定规则成立，无原文假成功，无部分review，原同事务一次释放免费次数或退100积分

#### Scenario: A11 Real isolated PostgreSQL preserves lifecycle races and accounting
- **WHEN** 在隔离PG/API中执行partial/零有效、幂等重放、旧claim/revision、源删和取消与迟到完成竞态
- **THEN** 原完成/退款/删除屏障及唯一账本关系保持，拒绝或取消后无正文复活，不重扣退，公共结果无片段内部数据

### Requirement: Explicit prompt versions preserve legacy behavior and current exports
新任务 SHALL 标v3并使用独立v3 Prompt/schema；Runtime SHALL 只传fresh已授权payload版本，v1/v2各原Prompt/原legacy count验证保持，未知/缺失版本外发前以已有固定runtime_internal_error失败，不回显未知值、不默认为v3。历史completed/meta、SCORE_VERSION、当前商务PDF/DOCX/事实确认/双get导出 MUST 保持。

#### Scenario: A12 New and historical versions follow explicit paths
- **WHEN** 创建v3、处理旧v1/v2 queued或读取历史completed，或输入未知/缺失版本
- **THEN** 新旧各走指定Prompt/验证器且不回填历史；未知版本0次外发固定失败，旧count守卫不放松，已保存稿和真实Word/PDF仍按原权限/revision导出

#### Scenario: A13 Injection and malformed transport never become control data
- **WHEN** source或模型输出包含注入、假ID定义、额外字段、说明加JSON、多对象/重复键、非stop、BOM或单一完整json围栏
- **THEN** source保持不可信资料，表只由server生成；仅原允许包装规范化，损坏或越权响应固定失败，异常/诊断/日志不含正文、位置、原响应或密钥

### Requirement: Optional real-Provider quality checks are bounded and isolated
本轮最多6个预冻独立纯合成样本各至多1次的真实质量QA SHALL 仅在root另行QA GO、固定candidate/Prompt/script/case、候选禁网无副作用先验及每例当前原完整七门禁有效空闲后执行。调用前持久独占marker、私有配置留服务器，不读用户/OSS、不创建生产job/usage/钱包/资料；任何失败/未知/超时 MUST 停止剩余，不自动重试/换模型/增预算/新目录绕过。只记安全结果/固定原因/计数/时长/实际请求数。

#### Scenario: A14 Six independent synthetic cases never become repeated sampling
- **WHEN** root明确GO后依次执行最多6个不同冻结用例，或其中一例失败/超时/请求状态不确定
- **THEN** 每例至多1请求、总<=6、marker先消费；失败后后例不开始且旧marker不清理，按真实事实报告，不修后自动重跑或创建真实任务扣费

#### Scenario: A15 Missing prerequisites or active user work blocks quality calls
- **WHEN** QA无明确GO、candidate/Prompt/script/case漂移、禁网先验不通过、七门禁非空闲/未知或私有隔离不能证明
- **THEN** 不调用Provider，不把本地替身/eval通过当真实质量结果；明确未执行/停止原因，原线上服务和用户工作保持，不进行生产切换或Git
