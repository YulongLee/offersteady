## ADDED Requirements

### Requirement: Professional CN PDF is the default saved-draft download
国服已有 PDF 导出 SHALL 默认使用单栏、受控高对比商务深蓝 A4 专业简历模板，以清楚的标题/联系信息、栏目分隔、经历子标题和列表层级呈现已保存稿。正文 SHALL 使用可阅读的固定基准字号、足够行距及一致页边距；不得强制一页、缩成极小字体或裁剪内容。PDF MUST 不加入产品品牌、AI 标记、评分/建议报告、照片、装饰进度条或未在稿中的栏目。原 DOCX 导出与 Global 共享 helper MUST 保持不变。

#### Scenario: Existing download yields a professional application document
- **WHEN** owner 从原下载入口导出已保存完成稿为 PDF
- **THEN** 获得真实 A4 PDF，采用专业单栏默认模板，正文没有品牌/评分/报告内容，原 API/MIME/附件下载语义保持

#### Scenario: DOCX and Global retain their original behavior
- **WHEN** 用户导出 Word 或 Global 现有两种格式
- **THEN** 原共享格式实现与既有导出表现保持，不因国服 PDF 模板改动而改变

### Requirement: Deterministic conservative structure recognition preserves content
模板 SHALL 只对当前已保存稿做确定性排版，保留全部可见内容、事实、数字、日期、联系方式、链接地址和原始出现顺序；不得新增/删减/改写事实或保存重排稿，不调用 AI、Parser、模型、OSS 或外部 URL。仅明确的 Markdown 标题/成对强调/列表标记、独立常见中英栏目名（可有末尾冒号或整行强调）与明确的经历子标题可形成层级；“教育：本科”等带正文的行 MUST 按完整正文保留。首行联系方式、长句或不确定行 MUST 不盲认姓名，不确定格式按原可见正文保留。原文第一行仅在短单行且非联系方式/栏目/长句、紧随最多 3 个非空页首行具有明确 email 或电话证据时，可按文档抬头排版；此规则 MUST 不创建姓名字段/新增事实，不以 URL 独占、日期/编号作为联系证据，无明确证据仍为正文。姓名/联系行仅可在已有位置形成页首，不从后文抽取日期、联系人或经历调序。

#### Scenario: Common plain and Markdown structures gain hierarchy
- **WHEN** 合成稿包含 Markdown 标题/列表、独立“工作经历”/“Education”等栏目、经历子标题及联系方式，或裸短首行后最多 3 非空行有明确 email/电话支持
- **THEN** 明确结构按相应层级排版；有明确联系上下文的裸短首行仅作为原文文档抬头，列表语法转为视觉列表，内容顺序、全部事实和地址保持，不新增姓名字段

#### Scenario: Ambiguous input is retained without invented structure
- **WHEN** 首行是联系方式/长句，裸短行无明确 email/电话证据或只跟 URL/日期/编号，或有“教育：本科”、未知栏目、混合标点及不确定格式
- **THEN** 不推测姓名、角色或缺失栏目，不丢内容或拆错字段；未知内容仍以完整普通文本输出

#### Scenario: PDF uses only the current saved revision
- **WHEN** 用户已编辑保存的稿不同于 AI 初稿、原文或目标岗位/JD
- **THEN** PDF 只渲染当前已保存 draftMarkdown，不混入原文/JD/评分/待补事实，不修改原稿、AI 初稿、素材或面试快照

### Requirement: Embedded real text remains readable and selectable
PDF SHALL 内嵌现有已许可中文字体，以真实文本提供可选择/复制的中文和混合拉丁字符，不把整页转为图片。字形覆盖检查、原输入 60000 字符上限和安全固定错误 SHALL 保持；不支持字符 MUST 明确失败而非悄悄丢字。HTML/XML 特殊符号或类似标签的输入 MUST 作为惰性文字，不执行脚本、激活链接或加载远程资源。

#### Scenario: Chinese and mixed-language content can be copied
- **WHEN** 导出含中文、中英技能、百分比、日期、电话、电子邮箱及 URL 的合成稿
- **THEN** PDF 内含嵌入字体与真实文字，文本提取包含全部事实与末尾标记，复制可读且没有外部资源或脚本动作

#### Scenario: Unsupported or invalid content fails safely
- **WHEN** 输入含缺失字形、空稿、超限或非法控制字符
- **THEN** 返回原有安全导出失败语义，不静默替换/丢字、不泄露正文，不收费或改稿

### Requirement: Long resumes paginate completely with clear hierarchy
模板 SHALL 自动换行和自然分页，支持中文、长经历描述及长 URL。栏目标题和经历子标题 SHALL 尽量与后续首段一起分页；长段落本身可分页，不能把超高段落强行绑定导致异常。每页文字 MUST 不重叠、不越出页边、不截断、不出现只有标题的孤立页或无内容空白尾页；正文原顺序及所有末尾内容保留。

#### Scenario: Long and boundary-case resumes render every page
- **WHEN** 导出多页经历、页末栏目/子标题、超长列表及长 URL 的合成稿
- **THEN** 可完整打开全部页面，所有事实和末尾标记存在，无越界/重叠/裁切/空白尾页，标题层级在分页后仍清楚

### Requirement: Existing private and free export guards remain authoritative
CN service SHALL 仅把默认 PDF 排版分发至 CN 专用模块。原登录/owner、completed、未删 source、当前 expectedRevision 和 factsConfirmed 守卫 MUST 在渲染前后继续复核；失败、过期 revision、更新/删除竞争 MUST 无文件交付。原 private,no-store、nosniff、二进制 MIME/UTF-8 附件名、导出不收费/不占次数/不写任务或钱包 MUST 保持。不得增加公开文件链接、持久化导出文件、正文日志或新接口。

#### Scenario: Owner confirms facts and downloads without a new charge
- **WHEN** 已确认事实的 owner 导出当前未删除完成稿
- **THEN** PDF 经原前后复核并私有返回，不增加优化次数、积分或其他账本/任务写入

#### Scenario: Unauthorized and concurrent stale exports return no file
- **WHEN** 未登录、他人、未完成、源删除、旧 revision 或渲染期间保存/删除的请求到达
- **THEN** 沿用原错误和权限边界，无简历文件或正文泄露，原已保存内容与费用保持

### Requirement: Formatting resources load lazily and rendering is bounded
字体/ReportLab 等资源 SHALL 仅在授权 PDF 导出路径延迟加载；通过独立字体名和有界锁等既有轻量方式隔离可变字体状态。等待不得无限，锁失败或渲染异常 MUST 固定错误并释放资源，不污染后续请求。内存/工作量 SHALL 由原输入上限、按需字节流和既有服务执行边界约束；不增加进程池、缓存、定时任务或实时面试执行工作。

#### Scenario: Concurrent exports and a render failure remain bounded
- **WHEN** 同时导出或模拟字体/排版异常
- **THEN** 有界等待后成功或安全失败，后续正常导出可继续，非 PDF 导入和面试路径不初始化字体/格式依赖

### Requirement: Local synthetic evidence precedes any production release
1–5.x本地开发阶段 SHALL 仅在与实际国服镜像绑定的本地工作区开发与自测，保留所有无关运行输入。验收 MUST 提供纯合成一页中文、两页以上长简历、中英文及边界样例的 PDF 和逐页渲染图，逐项核对文本/页尺寸/布局/保护回归，并提供本地可打开样例。不得读取真实用户简历、调用真实模型、修改线上/Git/Global/费用/数据库/依赖；生产发布需等待用户后续明确授权。

#### Scenario: User can review local output before deployment
- **WHEN** 本轮开发自测完成
- **THEN** 用户可本地打开带合成标记的模板 PDF 与逐页截图，得到真实测试结果及限制；国服生产镜像/容器未被本轮修改

### Requirement: Restrained business blue styling improves application-ready hierarchy
用户最新批准的5.x外观 SHALL 以白底深灰正文、深蓝标题/重点、受控淡底与左色条等局部矢量装饰强化抬头、栏目、经历层级和留白；具体色值、字号与绘制尺寸 MUST 在root实施GO前冻结。正文/联系/标题与其背景 MUST 高对比，灰度下仍可凭字号/层级/留白区分结构；装饰不能成为内容或改变真实文本阅读顺序。header SHALL 仅从原已识别title按原顺序包含最多后续4块contact/subtitle及仅紧随title的<=60字非句子body，后者仅展示分组、不生成role字段或改解析分类；遇任何不允许块 MUST 立即终止而不跳过。header真实完整wrap高度超过180pt或不适合时 MUST 全部回退原独立段落，回退title/navy和contact/深灰必须可读，不得白底白字，不缩字/裁切/重排。此要求明确取代首轮黑白外观，D1–12全部事实、内容/顺序、分页、私有免费导出、双重权限/当前saved revision和有界lazy守卫 MUST 保持。只允许CN renderer局部视觉及对应测试样例，不改Web/Global/DOCX/生成/Prompt/费用/接口/依赖，不新增照片、图表、评分、品牌或模板选择。

#### Scenario: Business blue visual refinement remains a faithful usable resume
- **WHEN** 按root冻结视觉生成两份用户样例及中文/中英文/长URL/页末/长段边界稿，并检查实际PDF和全部页面渲染
- **THEN** 新稿呈现冻结的深蓝抬头/浅底左色条栏目/经历层级与高对比正文，灰度用户样例仍可读；普通/无title/超高header与长label均按边界完整显示或回退，所有原可见文字/事实/顺序、可复制字体、自然分页/完整边界和D1–12守卫保持，无装饰重叠/裁切/大空白或新增内容，输出仅本地可审查，不代表生产已更新


### Requirement: Authorized production increment is pinned to the actual CN Backend baseline
6.x用户已明确授权将本地最终商务PDF部署国服，生产执行 SHALL 遵循本变更production-release.md；此前仅本地要求适用1–5.x历史，不代表已自动部署。root MUST 新鲜只读绑定实际image/container、完整输入/schema/Settings/有效配置/Compose/挂载网络及全部非目标/Web静态，冻结精确两源allowlist/service默认PDF分发AST与控制器输入支持SHA。默认只切CN Backend，Web/Global/DOCX/Prompt/模型/费用/DB/依赖/助手等 MUST 保持；真实漂移或无root实施GO MUST 不切换。

#### Scenario: A fresh actual baseline admits only the approved PDF increment
- **WHEN** root冻结本轮实际完整运行基线并审查两源/AST与全部非目标
- **THEN** 候选仅从实际父digest新增已验收renderer及默认PDF分发，原全部其它源/schema/Settings/有效配置/Web/static保持；未知变化停止，不用旧目录/健康字符串/标签代替实际组件

### Requirement: The actual candidate proves private real documents without production side effects
实际固定候选 SHALL 在禁网/只读/有限资源且不进入业务lifespan的探针中真实生成纯合成CN商务PDF和原DOCX，证明签名/MIME/A4、内嵌字体/可复制全文、字号/事实原序/尾标记、header回退/长段分页与原service授权屏障保持，七类副作用计数均0。MUST 不调用真实模型、不读取真实用户简历/账号、不写生产任务/钱包/资料、不新增镜像依赖；本地验收或伪文件头不能替代实际候选探针。

#### Scenario: A fixed candidate renders faithful synthetic PDF and unchanged Word
- **WHEN** 本轮实际候选执行固定纯合成导出探针及独立文件解析
- **THEN** 新模板与原Word真实完整可读、实际字号/全文/分页/回退符合已验收合同，完整源/schema/Settings与非目标保持且副作用0，不产生真实业务消费

### Requirement: Fresh protected-work gates control every production switch
preflight与真正切换前 SHALL 在同一发布排他锁且完整归属/输入复核后分别执行原固定七门禁，覆盖真实面试/租约/回答/mock/资料、有效未付订单/近期支付回调及CN optimizer jobs/usage，至少两次有效新鲜全零才切CN Backend固定digest。后台worker全部是非目标，不新增worker操作。发布器 MUST 在最终preflight/切换/恢复临近额外只读聚合实际Backend netns TCP8000 ESTABLISHED；正常部署须Running并实际读取，前后inspect同ID/image/StartedAt/Pid/完整归属Config及netns绑定，非零defer、读取/解析/身份未知停止，不输出socket地址。此聚合不改原七门禁或配置/TTL，不证明zeroinflight或原子无竞态。MUST 不结束用户、清理任务/租约、改TTL或放宽门禁。

#### Scenario: Valid active user work defers the release
- **WHEN** 任一真实受保护面试/优化job或其他活动非零，或实际Backend TCP8000 ESTABLISHED非零，且相关门禁/身份/netns读数有效
- **THEN** 仅protected_user_work_cutover_deferred保留原服务等待，不切换/结束活动/重复通知无变化，后续先重新核对实际归属和全门禁

#### Scenario: Unknown unreadable stale or drifting state stops automatic operations
- **WHEN** 门禁unknown/readfail/非法/缺字段/超限/过期/进程失败、TCP读取/netns或前后身份失败，或源/配置/控制器/归属漂移
- **THEN** 停止自动切换并报告，不能当忙碌静默重试、复用旧样本或触发无条件回退

### Requirement: Recovery restores only an owned fixed image and preserves user data
已知可恢复验收失败 SHALL 先核对本次精确归属，再于相同完整七门禁空闲且临近TCP有效0时恢复冻结旧digest/原有效配置；恢复不得改变任何用户任务、原稿、资料或已发生账本。普通命令失败/unknown/readfail/漂移 MUST 不笼统自动回退，活跃/归属变化/恢复失败须停止并报告。仅恢复本次精确归属candidate的已知cold-start exited失败时，两次inspect严格Running=false/Pid=0/Status=exited、Restarting/Dead/Paused均false、同ID/image/StartedAt及其余完整归属/Config不变，才可输出明确stoppedProcessProof替代TCP读取；MUST 不声称读到0 sockets，原七门禁仍须全部空闲。该例外MUST NOT用于preflight/正常部署或Running时exec失败、未知/restarting/dead/归属变化，不关闭连接或改变restart策略。

#### Scenario: An owned known failure can restore the frozen old image
- **WHEN** 本次目标已切候选、出现已知可恢复健康/验收失败且归属与全部门禁有效空闲，运行时TCP真实0或严格满足本次candidate的双确认stoppedProcessProof
- **THEN** 只恢复本次固定旧digest并验证实际健康/原配置，若用停态证明须与真实TCP读数明确区分；用户内容/任务/真实账本保持，不删数据或回放任务

#### Scenario: Lost ownership or unreadable state never triggers an unsafe recovery
- **WHEN** 回退前出现新受保护活动/TCP非零、Running时读取失败、普通命令失败、未知/restarting/dead或归属/源码配置漂移
- **THEN** 停止自动恢复并报告，不能覆盖他人发布、绕过门禁或声称已恢复

### Requirement: Independent production verification is scoped and privacy preserving
发布完成后 SHALL 独立核对实际container/digest/归属、冷启动健康/重启、完整源/schema/Settings/配置、全部旧Web静态/NGINX/非目标与共享tag，真实公共入口及匿名optimizer401/private,no-store；只做实际窗口脱敏ERROR/traceback/HTTP5xx/固定诊断统计。MUST 不代用户登录/导出真实稿/创建真实测试消费、不输出原日志或私有配置、不把短时结果冒称长期性能。只有真实验收完成才能更新发布任务/记录并通知用户测试。

#### Scenario: Actual release evidence supports normal user testing without synthetic production writes
- **WHEN** 候选切换后独立verify与脱敏短观察完成
- **THEN** 实际固定目标健康、完整原功能/schema/配置/Web非目标和匿名守卫符合冻结值，记录真实窗口/未覆盖限制并通知用户原页面自测，不把本地通过或未执行分支当生产事实
