# 国服专业简历 PDF 本地验收

当前状态：国服已完成本轮单Backend模板增量发布、独立verify及180秒观察，双根strict/链接收尾通过，共16/16任务。实际生产结果见本文6.x。

首轮历史状态：首轮6d版本7/7本地任务和下列D1–12已通过，**未部署**。用户最新反馈外观太素，现追加5.x专业商务深蓝本地计划；root已提供视觉冻结值，本轮四项任务与D13尚待严格校验/实施GO，不能将首轮154/586/11页结果当成新外观验收。生产发布仍需后续明确授权。

## 首轮已验收范围与冻结（历史保持）

- 依据 [proposal](proposal.md)、[design](design.md)、[能力规范](specs/cn-resume-delivery-template/spec.md)、[任务](tasks.md)；[本地记录](../../../docs/releases/cn-resume-delivery-template-local-20261018.1.md)。旧 [CN 合同](../add-cn-resume-optimizer/contract.md) 的权限/事实/金融/删除规则保持。
- 本轮新鲜只读基线 `current-runtime.json` SHA `39ee2323bf893db536bd677bf949be9781e0961bfbbd25d9fba9c1cf28a1be68`：Backend f6dbe8fd…、Web2124eee8…；230原输入绑定国服工作区。
- 最终新增 renderer SHA `6d466a27fef9bc5454420e00913c8bbb3275b6264cabc80e370de446ccb3d7db`；CN service SHA `4caa2319066a654320f07527dac5243d0431b7382a57a8e1e1d4d0dbba0e2d66`。`local-input-manifest.json` 冻结9项核心输入，Web辅助测试/预览源另由 `web-build-exclusion.json` 绑定。
- 独立 `source-preservation-review.json`：230原输入229逐字保持，唯一既有源变化是CN service默认PDF分发；整模块AST将该分发归一后与实际基线相同。共享helper/字体/费用/Prompt/schema/mock及9项Web导航/计费/资料等源保持，Page仅替换导出说明一段。
- 只实现 CN PDF renderer、最小分发、简短说明和test-only合成预览。没有线上写入/部署、真实用户简历读取、真实模型调用、数据库/配置/依赖变更或Git操作；无AI行为变更，不新增AI eval。

## 首轮实际验证（6d版本，不代表新外观）

- `final-natural-combined-junit.xml` / `final-natural-combined-tests.txt`：**154/154通过，0失败/0错误/0跳过，30.013秒**；含65项新PDF、11项原共享导出、16项新隔离PG/API和62项既有CN service测试。测试SHA见核心manifest。
- `web-vitest.json`：**586/586通过**；typecheck与正式production build实际完成。`web-build-exclusion.json`扫描83文件：正式输入仅index/guide，样例、桥接URL/头标记和PDF均未进入build。该本地标准build不是未来生产静态全集overlay发布包。
- `pdf-generation.json`：7份纯合成PDF，**11页**，逐份实际PDF签名/MIME/A4/内嵌字体/全文顺序/末尾/无动作资源检查通过；experienced1页、campus1页、plain-header1页、long-mixed2页、long-url2页、page-boundary2页、long-paragraph2页。本地渲染耗时6.7–98.2ms，仅合成样例结果，不代表线上容量。
- `pdf-geometry.json`：独立pdfplumber检查11页文字边界/行间重叠均通过、图片0。`visual-review.json`：root实际逐张查看全部11张最终Poppler渲染PNG，无裁切、重叠、孤立标题、空白页或可避免的首页巨大空白；视觉不是用文本提取或几何检查代替。
- `independent-audit/final-boundary-pdf-checks-v3.json`：最终SHA绑定的13项独立边界、68页实际文本/顺序/A4/逐字45pt左右边界通过；含60000字符、标点/长URL、长正文/列表、14标题链及22/32/39/44条既有内容后的分页。该68页检查是机器文本/几何/正文起始验证，不宣称逐页视觉查看。
- `preview-http.json`：**20/20通过**。真实PDF58164bytes，SHA `c547cfe9f10645784d7881ab3bb0b0b2277a16111d1e011d5b1cc9713699858d`，全文精确对应浏览器保存revision2并含SavedDraftQA91；原DOCX为真实文件且同稿。Origin/端口/固定头/路径/字段/类型/长度/控制字符/预检等本机边界均通过。
- `browser-qa.json`、3份DOM及2张截图：真实Page编辑后清空事实确认并禁下载→保存revision2仍需重新确认→确认后Word/PDF均显示下载成功→恢复干净合成样例。模拟面试导航仍可见，原事实确认/dirty/revision行为保持。
- IAB download event没有提供磁盘文件路径，**未宣称抓取浏览器落盘文件**。界面动作成功与相同已保存稿的真实本机HTTP字节/解析校验分别留证。桥接首次PDF在最终6d源码冻结后导入，源码SHA与HTTP报告一致。

## 场景核对

| 场景 | 实际证据与结果 |
| --- | --- |
| D1 Existing download yields a professional application document | 最终真实CN service/API、20项HTTP和浏览器PDF成功；7稿11页A4专业单栏视觉通过 |
| D2 DOCX and Global retain their original behavior | 共享helper/字体源SHA不变，11原格式回归及CN DOCX精确OOXML部件/本机真Word通过；未修改Global服务 |
| D3 Common plain and Markdown structures gain hierarchy | 65新PDF回归覆盖精确栏目/经历/列表与CN/EN裸短首行近邻明确email/电话，保持原顺序；plain-header及两用户样例已视觉确认 |
| D4 Ambiguous input is retained without invented structure | 联系首行/长句/日期URL假联系/编号/带正文栏目/未知格式均有正反回归；不新增姓名字段或事实 |
| D5 PDF uses only the current saved revision | 新PG/API的保存稿与原文/初稿/JD互异；浏览器revision2同稿HTTP全文精确匹配，编辑后必须保存重确认 |
| D6 Chinese and mixed-language content can be copied | 7稿真实文字/内嵌字体/全文顺序/数字日期联系方式URL/无动作资源通过，单栏非图片 |
| D7 Unsupported or invalid content fails safely | 空/超限/控制/缺字固定错误与锁异常恢复回归通过，无静默丢字或正文错误泄露 |
| D8 Long and boundary-case resumes render every page | 最终11页独立几何+root逐张视觉通过，长段自然从首页开始；68页独立机器边界通过，无删字或极小字号压页 |
| D9 Owner confirms facts and downloads without a new charge | 新隔离PG/API覆盖免费与积分原消费后导出零新增usage/钱包写入，原factsConfirmed保持 |
| D10 Unauthorized and concurrent stale exports return no file | 新16项PG/API及旧62项CN覆盖未登录/他人/未完成/源删除/旧revision及渲染间保存/删除，无文件交付 |
| D11 Concurrent exports and a render failure remain bounded | lazy导入、共享2秒锁、锁失败不误释放、异常恢复、新旧PDF混合并发及文档隔离均通过 |
| D12 User can review local output before deployment | 两份真实合成样例PDF、全部页面图、外层醒目合成提示预览及实际HTTP下载可用；样例/bridge未入生产build，线上未改 |

## 修复过程与实际限制

- 初次新service测试有1项尾换行期望不符：实际保存稿本来strip，修正测试期望后合并通过；`service-tests-initial.txt` / `service-junit-initial.xml`保留，不宣称初次全通过。
- root真实几何发现旧long-url中文句号悬挂越界。修复按当前字体/字号的最大悬挂标点advance预留内缩，保留字号/全部字符/全局禁则，新增4项真实坐标回归；未放宽QA边界阈值。
- root旧12页视觉发现旧long-paragraph首页仅标题/联系、正文整段被keepWithNext搬页。`visual-review-before-pagination-fix.json`保留失败；最终CN局部HeadingStartGroup只将fit预算约束为标题链+真实split首2行，原完整段落自然分页，新增5项真实PDF回归，最终长段2页而非旧3页。
- 旧37/145/149等阶段测试和e3/81a边界报告保持历史SHA，不能替代本最终6d验收。当前最终证据以154项、7稿11页和v3边界为准。
- 仅纯合成材料；未使用真实用户简历、不测试生产流量/所有招聘系统。未知/奇特结构保守输出正文，不承诺复刻原文件版式；用户仍需核实事实。Word保持原模板。
- 本轮仍只本地。后续生产需用户明确授权，并重新冻结届时实际镜像/完整静态与用户活动门禁；本地通过不等于生产GO。

证据均位于主工作区 `/Users/liyulong/liyulong/1_projects/offersteady/artifacts/cn-resume-delivery-template-20261018/`。root最终确认：双工作区strict均exit0，6份Markdown各13条文件链接存在、双根文档一致，任务4.1完成；见final-validation.json。

## 5.x 商务深蓝视觉追加（本地实现、验收与交付已完成，保留历史）

用户已授权更漂亮的标准模板，本轮明确修订原黑白要求为受控商务深蓝。只修改CN renderer局部矢量绘制/颜色/字号留白及相应纯合成测试；原解析分类/事实/文本顺序、当前已保存稿、双重权限/revision屏障和D1–12守卫保持。Web/service/Global/DOCX/Prompt/生成/费用/DB/依赖/接口均未改。首轮7/7、6d版本D1–12及所有失败历史保留，本轮结果单独记录。

### 最终冻结与实际执行

- 最终renderer SHA `76925432e1c8c7ac7801e8cc4978fba67641af65f8c1a7e748bf0593fc0f523d`；puretests SHA `5bcde6dd7cf9403b4466ef28f02a2958bbd9e9ceaee7734c7ecbc46640f5733d`。root本地GO、冻结设计和本轮证据均在 `artifacts/cn-resume-delivery-template-business-20261018/`。
- `final-combined-junit.xml` / `final-combined-tests.txt`：**170/170通过，0失败/0错误/0跳过，约34.6秒**（81新PDF纯测试+11原共享导出+16既有隔离PG/API+62既有CN service）。仅有1项原第三方deprecation warning，无新依赖或错误。
- `pdf-generation.json`：**10份纯合成PDF、14张彩色页及2张用户样例灰度页**。experienced/campus/plain-header各1页，long-mixed/long-url/page-boundary/long-paragraph各2页，header-fallback/no-title/long-section各1页。新用户样例使用business-experienced/campus命名，前轮PDF与20261018.1记录保留。
- `pdf-geometry.json`：独立pdfplumber实际检查14页全部文字glyph及矢量装饰边界、行间重叠，均通过；实际文字前景/背景对比均>=6.9。真实文字/字体/A4/全文顺序与末尾保留，不将文字图片化，不加载远程资源。
- `visual-review.json`：root逐页实际查看最终14张彩色及2张灰度渲染页，无裁切、重叠、孤立标题、首页大空白或碎尾；两用户样例各1页，灰度下中文及层级仍清楚。此为合成样例视觉检查，不保证所有打印设备或ATS。
- `preview-http.json`：**6项实际本机检查通过**。两份样例HTTP字节分别与最终PDF严格相同；修改输入实时生成当前文字、原Word同稿真文件、foreign Origin无内容拒绝、5178外层合成预览返回200。最终experienced SHA `8c2a376fa578150118b0ed025cafa24b3d140877cf4d311b96602054a638a996`，campus SHA `55c2bebf84d3c061c31a75909b4dff0a19d79fedd7f6120c5027fad81d6f3d92`。
- 本轮**未重新执行浏览器交互、Web586、typecheck或production build**。相关Web/桥接源未改，只复用首轮已验收浏览器/revision和83标准build排除样例的历史证据；不把旧结果冒充新执行，也不声称抓取新的浏览器落盘文件。
- 独立 `final-source-preservation-review.json`：旧9核心输入中允许变更renderer/puretests，其他7项逐字保持；旧230实际运行输入仍只有前轮CN service差异，其他229项保持。原parser/分类/公开入口AST不变，仅_render_pdf视觉实现与展示分组selector增加；Web/shared helper/font/fee/Prompt/mock保持。
- 独立 `final-business-header-review.json`：最终769绑定的11项抬头边界/12页机器验证通过，覆盖原序最多后4块、不跳不允许块、无title、>180pt整体回退无白底白字、26pt标点、长段首页起始及真实glyph边界。root全部样例视觉为另外的14+2页证据，不冒领该12页为逐页视觉检查。

### D13与相关守卫复核

| 新增/复核项 | 本轮实际结果 |
| --- | --- |
| D13 Business blue visual refinement remains a faithful usable resume | 冻结深蓝band、浅底左色条栏目、经历层级和高对比正文实现；14彩页+2灰度实际视觉通过，真实文字及顺序完整；无新字段、品牌/评分/照片/图表 |
| D1–12内容/分页/有界保护 | 170项完整相关回归通过，包含原共享导出、CN权限/删除/revision/无收费写入、锁/lazy、字体/事实顺序及长URL/长段自然分页；原解析AST保持 |
| 保守header与装饰边界 | 真正wrap<=180pt才画；176pt可用/189.5pt全回退有真实PDF回归；连续selector遇不允许块立即终止，fallback title/navy与contact/深灰可读，长栏目完整增高 |
| 新样例与真实下载 | 10份14彩页及2灰度、两用户各1页、6项本机HTTP完成；桥接/Web未改，无新浏览器或Web build执行声称 |
| 非目标与本地交付收尾 | 源SHA独立复核通过，首轮产物/记录保持；任务5.4的双根strict/链接与本地交付已完成，当时无生产GO |

### 校准历史与限制

早期bddd…版本的long-mixed出现3页、尾页只有1行标记，root与独立视觉均判为不通过。root只批准统一entry spaceBefore从6pt微调到5pt，未缩字号、改正文/fixture或特判样例；最终769恢复2页，固定12项目稿有真实回归。早期视觉/旧SHA证据保留，不宣称早期即通过。

本轮没有线上写入/部署、真实用户简历读取、真实模型调用或Git操作。只交付本地商务蓝模板，原会员/积分/下载政策保持。生产仍需用户后续授权与届时实际镜像重新冻结；本地170项与合成页面验收不代表生产已更新。

Root5.x最终本地收尾：全部实际验收通过，11/11任务；[20261018.2本地记录](../../../docs/releases/cn-resume-delivery-template-local-20261018.2.md)。双根strict/Markdown文件链接与源码冻结终检记录于business证据目录final-validation.json；仍不构成生产GO。


## 6.x 国服上线授权与生产验收（6.1–6.5及独立审查、文档收尾已通过）

用户现明确授权将已验收商务PDF模板部署国服并自行测试，执行[生产追加规范](production-release.md)。1–5.x的11/11本地、769最终源码、170测试/14彩页/2灰度/6HTTP和所有旧失败保持历史，不代表6.x已上线。默认仅CN Backend两源增量，现有Web下载入口可触发新模板；Web说明/静态不在当前发布范围。

| 生产场景 | 证据映射与后续收尾要求 | 当前状态 |
| --- | --- | --- |
| D14 A fresh actual baseline admits only the approved PDF increment | `current-baseline.json`、`root-source-baseline-review.json`、独立`fresh-baseline-source-review.json`与`root-implementation-go.json`绑定f6/2124、230/202/340/315、Web第7非目标及两源230→231；final-2冻结/独立审查与`actual-candidate-summary.json`绑定6f9候选、父Config全等及92→93层；实际deploy/verify完整源/配置/非目标保持 | 基线、候选与实际两源单组件切换验收完成 |
| D15 A fixed candidate renders faithful synthetic PDF and unchanged Word | `prepare.json`、`candidate-evidence.json`与独立`actual-candidate-review.json`绑定实际6f9候选禁网/只读/限资源；10份真实合成PDF共14页与本地已验收文件逐SHA相同，原Word同稿部件/前后get/facts/owner/revision/删除及注入守卫保持，231源/202schema/340Settings与七类副作用0 | 6.2实际固定候选验收通过；与本地演练证据分开 |
| D16 Valid active user work defers the release | `preflight.json`与`preflight-evidence.json`七门禁全有效空闲/TCP0；`root-cutover-go.json`后deploy临近重新完整七门禁全有效空闲，`deployment-evidence.json`最终TCP atMs1792342349031为0且netns绑定，随后只切Backend固定6f9 | 两次实际保护均通过；未发生生产busy/defer，忙碌分支仅工具回归 |
| D17 Unknown unreadable stale or drifting state stops automatic operations | final-2控制器/TCP96项回归与独立`final2-controller-payload-review.json`、`final2-freeze-receipt-review.json`覆盖unknown/readfail/drift/过期/Pid/netns失败停止；final-1审核纠正另保留 | 最终工具回归/独立审核通过；未发生的生产失败分支不冒称实际执行 |
| D18 An owned known failure can restore the frozen old image | final-2工具回归绑定精确归属/七门禁+实际TCP0或仅恢复exited双确认stoppedProcessProof、冻结旧digest和数据保持 | 工具回归/独立审核通过；实际发布成功，无生产失败/恢复/回退，不冒称已恢复 |
| D19 Lost ownership or unreadable state never triggers an unsafe recovery | final-2负例覆盖Running读取失败、未知/restarting/dead/paused、新活动/归属变化及不能滥用停态证明；实际新2a907/6f9归属由deploy/verify/observation一致绑定 | 工具回归/独立审核通过；未发生生产失去归属/未知恢复分支 |
| D20 Actual release evidence supports normal user testing without synthetic production writes | `deploy.json`/`verify.json`各9项公共/匿名检查通过，新2a907/6f9及完整231源/202schema/340Settings/有效配置、315静态/NGINX/7非目标保持；初始53.214秒134行与`observation-final.json`实际180秒406行均无截断，新容器healthy/restart0，ERROR/traceback/HTTP5xx/诊断均0；独立`final-release-review.json`通过并绑定实际证据 | 实际deploy/verify、最终短观察和独立上线审查通过；root最后strict/链接及6.5收尾通过 |

### 已完成的6.1与初始只读观察

新鲜只读基线已绑定：`artifacts/cn-resume-delivery-template-20261018-release/current-baseline.json`，SHA `007c9fddb42158eb214be28ceac2e2922a89552d38ad67a44c9d0c606d4c63b5`；实际Backend50bcb/f6、Web88ae/2124，230/202/340/315，精确两源230→231，Web并入第7非目标。`root-implementation-go.json`实际记录用户授权、完整context/源审查、双根strict通过、Backend-only两源实施GO及后续实际候选审查/七门禁/TCP前提，且`deployed=false`。6.1完成只允许按合同继续准备，不能视为候选或发布通过。

`initial-activity.json`为只读聚合初始快照：七门禁均合法有效空闲，生产写入/Provider调用为0。它没有替代最终preflight、切换临近和必要恢复的完整重读，也没有证明TCP/netns保护或发布完成。DockerStopTimeout null/无explicit graceful参数，不证明zeroinflight；额外TCP和严格停态恢复证明仅降低瞬时风险，既有金融门禁不代表后台worker管理。

### 工具修复历史与已完成的6.2

本地首稿探针失败报告`local-probe-rehearsal-failed-draft1.json`保留；随后本地探针/71项工具测试曾通过，均不等于实际Docker候选验收。final-1控制器SHA`054856ce…`的早期独立报告误将容器ID/镜像检查视为完整4.1证明；root发现未显式比较目标Pid/进程状态及host目标netns与exec self/init netns，已阻止final-1继续。原报告保留为`independent-audit/final-controller-payload-review-final1-original.json`，`final-controller-payload-review.json`纠正为`passed=false`。不以先前71项通过掩盖审核发现，也未把工具问题写成线上故障或生产回退。

final-2已仅修复该证明并冻结：`local-release-tools-freeze-final-2.json` SHA`a6208648bfa63df14dc64d9e70c2e11db640a73696cf3e65bd24b47bc0a2f119`；controller SHA`0feeabe630f14c235260ab0de0a2d0b36aea43a5a42942ea34bd8a2a518325c7`、input SHA`0aa27bfb3eaac0e5a65f17bcc046215fc07217e37b0c888b71e8cb425e31a92c`、TCP支持SHA`4d102932c1076a89126144a0687d7519345c3fcf4a50cf960d6ff4eb3591d291`，probe SHA`827209bff1882117de510d6893f5632082495ccde5a3f6b23c1a82bc0ea03d0f`保持。96/96工具回归通过，显式前后Pid/Running/Restarting/Dead/Paused、host目标netns与exec self/init绑定和失败停止；原七门禁/两源不变。独立final2-controller-payload-review与freeze-receipt-review均通过，工具审核阶段与真实候选分开留证。

实际`prepare.json`结果prepared=true、productionChanged=false，候选固定为`sha256:6f9a55d8503971265e88dd97a8db804a0b3a7d8a785dc14320fc7fb54b3e443f`，父为本轮f6固定digest。`actual-candidate-summary.json`核对Image Config全等、原92层RootFS前缀完整/候选93层、7非目标保持且原f6服务在读取时仍运行，未导出私有环境。实际禁网只读候选`candidate-evidence.json`真实生成10份14页合成PDF，逐源SHA/PDF SHA/页数与769已验收文件相等；原DOCX部件/默认分发/注入导出/前后两次get及权限修订守卫通过，231源/202完整schema/340Settings保持，无新增路由，七类副作用计数和业务/计费写入均0、未进入lifespan。独立`actual-candidate-review.json` SHA`7f5311b649dd0aec9a565e80110895b3279ae8177ef89dbf9099fc0ff8b6126d`通过，证明候选而不代替冷启动/实际业务运行态验收。

`preflight.json`为preflightPassed=true/productionChanged=false；完整七门禁均有效空闲，TCP实际0并绑定netns摘要。`root-cutover-go.json`已在实际候选审查后记录受保护切换GO，明确deploy仍须临近重复全部七门禁和实际TCP；其deployed=false不是发布成功。准备阶段截至当时仅完成6.1–6.2。

### 已完成的6.3–6.4：实际切换、独立verify与短时观察

`deployment-evidence.json`确认deploy临近重复原完整七门禁有效空闲，TCP atMs`1792342349031`实际0、前后进程/netns绑定后，记录switch intent并只切CN Backend。`deploy.json`为deployed=true，新容器`2a9070321263a2a57ecb8c3e20edef63f5bbabfc7e765062094d00a42fa25f90`，实际镜像为已审`sha256:6f9a55d8503971265e88dd97a8db804a0b3a7d8a785dc14320fc7fb54b3e443f`，StartedAt=`2026-10-18T16:52:37.493571389Z`（上海2026-10-19 00:52:37）。原f6固定回退镜像保留；实际未发生busy/defer、发布失败/恢复/回退或代理reload，不以工具分支冒充生产执行。

`verify.json`为verified=true，独立实际核对相同新归属、冷启动及完整231源/202schema/340Settings/effective config、315原Web静态/NGINX和7非目标保持。deploy与verify各完成9项检查：healthz、login、build、简历优化、模拟面试、普通面试、笔试7项200，原Web HTML/build摘要保持；匿名optimizer capability与无效合成路径export各401/private,no-store。没有登录真实账号、创建生产job/usage/钱包/资料/面试、读取用户稿或调用真实模型。

deploy/verify输出中的`components.backend.signature.health=starting`取自切换意图/progress历史签名，不能当作后续实时健康状态。实际健康验收由控制器当前检查及`observation-initial.json`确认：相同新容器running/healthy、restart0；自新目标启动覆盖53.214秒、134行，4000行上限未截断，ERROR/traceback/HTTP5xx/fixedFailureDiagnostics/unknownDiagnosticMessages均0，未导出原始用户日志。

最终`observation-final.json`另核对相同新容器/image仍running/healthy、restart0；实际窗口atMs`1792342387231`至`1792342567231`，完整180.0秒、406行/4000行上限、mayBeTruncated=false。ERROR/traceback/HTTP5xx/fixedFailureDiagnostics/unknownDiagnosticMessages均0。该真实短观察不代表长期P95、所有真实简历或打印/ATS兼容，初始观察文件和原窗口不覆盖删除。

独立`independent-audit/final-release-review.json` SHA`7b98961d252b42dca56d037358038f1c3883db0b550f43fad85192419e5c17e1`实际审查通过、findings为空，绑定完整基线/工具/实际候选、重复七门禁/TCP0、真实切换/独立verify及最终180秒406行观察；它未执行SSH/Docker、额外生产写入/模型/用户稿读取或Git。此前失败历史保持，未发生的生产恢复分支仍只由工具回归证明。

6.5的[生产记录](../../../docs/releases/cn-resume-delivery-template-20261019.1.md)与root最后双根strict/链接收尾通过；最终清单见发布证据目录final-validation.json。日志原文、socket地址、用户/简历/会话标识与私有配置不进入本地记录。

服务器目录 `/opt/offersteady/releases/20261019-cn-resume-template-1`；本地目录20261018只是任务产物名。当前6.1–6.5及独立上线审查、文档收尾已完成，总16/16；实际Backend已切换并通过verify和180秒观察。真实模型、用户简历、生产测试job/usage/钱包/资料、压测、Git/Global/助手仍未授权。线上日志仅聚合，私有配置留服务器。
