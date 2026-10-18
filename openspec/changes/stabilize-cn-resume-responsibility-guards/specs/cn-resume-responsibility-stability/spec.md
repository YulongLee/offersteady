> 当前生产目标以用户明确选择的R13回退为准，R12的v6部署仅保留历史。

> 最新V6以R12为准；V4/V5均已停止不得发布，旧计划保留历史。当前最后6例单次验证，已消费5次，总<=12。

> R1–R8中版本名/7源236计数只描述历史v4；R9–R11为已停止v5计划。当前仅R12的v6（12源241、最后6例）作为上线验收，继承之前的事实/金融/排版和完整生产保护。旧失败保留，不计为阶段全通过。

## ADDED Requirements

### Requirement: V4 distinguishes explicit third-party participant nouns conservatively
V4 SHALL 仅跳过精确“其他参与者/其它参与者/其余参与者”内的参与词素作为候选人有限责任谓词，其余限定与所有强责任/英文/数字/实体/否定/技术等守卫 MUST 保留；同一谓词用于片段、对应变化行格与最终稿，不接受模型开关。

#### Scenario: R1 Third party noun substitution is allowed without a responsibility change
- **WHEN** 纯合成源只将“便于其他参与者继续处理”改为“方便其他同事继续处理”且其余事实/结构有效
- **THEN** v4可应用该实质修改，v3旧规则仍拒绝，未编辑文本不变

#### Scenario: R2 Real or mixed candidate responsibility remains protected
- **WHEN** 源“我参与登记并协助其他参与者”变为无候选人限定，裸参与者消失、强责任增加、英文责任升级、数字/否定/技术跨行格改动
- **THEN** 原固定原因拒绝；第三方称谓不能掩盖候选人责任，不能泛化忽略全部参与者或降低其它事实门槛

### Requirement: Versions and financial contracts remain compatible
V4 SHALL 使用独立Prompt和既有编号内部schema；新任务默认v4，v1/v2/v3各原Prompt/验证，未知版本外发前失败。公开API/会员3次/100积分/partial/零有效退款/权限/claim/revision/source/cancel及导出 MUST 保持。

#### Scenario: R3 Version routing and old results remain intact
- **WHEN** 新v4任务或历史v1/v2/v3及未知任务执行
- **THEN** 仅新v4启用窄谓词，旧分支保持，未知0HTTP，历史结果不回填；原90s/6500/256KiB/并发预算不变

#### Scenario: R4 Success or rejection settles or refunds exactly once
- **WHEN** 隔离真实PG/API执行免费/积分partial成功、零有效或全局无效并重放，或取消/删除/修订屏障胜出
- **THEN** 合法稿一次settled；未交付一次released/退款，迟到不复活；真实PDF/Word及双get保护保持

### Requirement: Synthetic quality verification is bounded and truthful
v4历史阶段 SHALL 冻结八个独立纯合成case，各至多1请求、该阶段总<=8（实际在4次后停止）；候选禁网只读先验及每例当前完整七门禁有效空闲后，先持久marker再外发。失败/未知 MUST 停后例，不自动重试或清旧marker；配置留服务器，不读用户/OSS/真实任务、不写生产job/usage/账本。

#### Scenario: R5 Model quality is separately verified and failure stops the run
- **WHEN** 固定candidate/Prompt/script/cases获得本轮root GO并依次执行
- **THEN** 每例必须产生至少一处安全实质修改才成功，记录实际计数/时长；任一失败停止，无原文假成功，不将本地替身当真实模型质量

### Requirement: CN release is incremental and protected
仅全部质量/回归及实际候选通过后 SHALL 发布CN Backend固定digest；完整原229非目标输入/202schema/340Settings/Web315和七非目标 MUST 保持，原10PDF/Word不变。发布 SHALL 使用[保护流程](../../design.md)的排他锁、两次完整七门禁与临近TCP/netns检查，busy等待、unknown/drift停止，不终止用户。

#### Scenario: R6 Current image and all unrelated features are preserved
- **WHEN** prepare/实际禁网探针与发布后verify
- **THEN** 候选由实际6f9派生，精确七文件delta/236输入，完整schema/config/Web/非目标及真实导出保持，副作用0；已部署不重复重启

#### Scenario: R7 Protected work defers and guarded recovery retains data
- **WHEN** 任一保护活动或TCP非零，或读取未知/归属漂移，或已知候选健康失败
- **THEN** busy保持原服务等待；未知/漂移停止；仅归属本次且原保护仍全通过时按固定旧digest恢复，严格停态证明不冒充0socket，不删除数据或改用户消费

#### Scenario: R8 Actual rollout is checked before reporting complete
- **WHEN** 固定候选切换成功
- **THEN** 完整verify及健康/登录/普通模拟笔试/简历入口和匿名401缓存控制通过，短时脱敏ERROR/traceback/5xx按真实覆盖范围记录，才通知用户测试；无Git/其它组件发布


### Requirement: V5 server-owned layout and short edit units replace whole-fragment copying
V5 SHALL 按设计生成最多24个8–144字符正文可信单元，readonly完整片段仍供evidence；内部edit仅unitId/replacement，未知ID固定拒绝、额外fragmentId/offset/schema字段全局失败。所有换行/prefix/标题/空白/表分隔/pipe/格边缘由服务器保留，replacement不得含CR/LF/pipe/HTML；所有数字/机构/技能/责任等原事实及v4窄谓词、对应行格和最终稿守卫 MUST 保持。只读来源完整不截断，重复单元输入共同32KiB额外预算，原90秒/6500/256KiB/并发不变。

#### Scenario: R9 Short edits keep layout while the old whole-fragment format error rejects
- **WHEN** 合成Markdown含CRLF/list/table等，v5只提交单元正文措辞修改，对照v4构造省略换行/pipe的整体提议
- **THEN** v5原排版逐字符保留且安全实质稿交付，v4原构造仍拒绝；这不是实际第4例输出的断言

#### Scenario: R10 Units cannot move or fabricate facts and versions remain fixed
- **WHEN** 单元未知/重复合格/改责任数字技术/跨格借事实、含换行pipe/额外offset、或执行v1–v4历史版本
- **THEN** 原全局/逐edit/全相交/partial零有效退款规则保持，旧版本原路；v5既有API/wire无内部unit字段，历史不回填

#### Scenario: R11 Corrected v5 quality and rollout require new exact evidence
- **WHEN** v4第4例失败后进入本轮有据修正的v5冻结验证
- **THEN** 保留旧失败与4已消费marker、不开始旧后例；v5另冻八例各一次，合计<=12，失败/未知停止不续调；只有新239输入固定候选全部QA及完整保护通过才发布，不沿用旧b78或七源控制器


### Requirement: V6 dimension names are server-defined and structure remains strict
V6 SHALL 将模型dimensions限制为固定具名评分对象，四必填字段及仅有JD时的roleMatch，unknown/missing/score类型/依据等 MUST 仍全局失败。只在完整类型验证后按服务器固定key恢复旧公开数组，不填充默认分数/伪造成功，v5单元/事实/结构/金融规则保持。原v1–v5各原路，v6选择官方已知支持的结构化模式，未知网关不猜能力；数据完整验证永不省略。

#### Scenario: R12 Corrected named scores and final bounded acceptance
- **WHEN** 服务器明确requiredDimensions、模型输出固定字段，或缺失/多余/JD不匹配；修正v6执行最后六个固定合成用例
- **THEN** 合法对象唯一恢复完整四/五旧维度，缺失/多余等全局失败；不得伪造/忽略错误。六例各1调用，前两阶段5次保留，总<=12且失败停后例；只有新241输入候选本地与真实6例、实际全部保护及正式发布验证通过才上线


### Requirement: User-selected historical content and PDF are restored without data loss
用户要求回退且已明确选择同时恢复改写逻辑和PDF时 SHALL 用新鲜实际8c基线与独立受保护计划切回10月18日正式固定f6dbe镜像，241→230且其余228输入/schema/有效配置/Web/7非目标 MUST 保持。新任务恢复v2及旧PDF；已完成v6结果/用户保存稿及真实费用 MUST 保留，不自动回填、重放、清理或改账本。所有原完整七门禁/实际TCP/netns/归属/未知停止/受保护恢复 MUST 继承；忙碌只等待。上线前旧目标真实禁网230/202/340、真实Word/PDF与纯合成v6已存结果兼容检查通过，部署后完整verify/9公共检查与短时脱敏观察才能报告成功。

#### Scenario: R13 An explicit rollback restores both yesterday behaviors and preserves current data
- **WHEN** 用户选择“改写逻辑和 PDF 模板都恢复到昨天”，新鲜实际基线/固定旧镜像和所有保护通过
- **THEN** 单次CN Backend切为f6dbe，旧v2和原PDF生效，原用户数据和费用保持；完整230源/202schema/340Settings/315Web/7非目标与健康验收通过，实际观察范围如实记录。活动非零等待，未知/漂移/失败按既有保护停止或已知受保护恢复，不重复重启已完成目标
