# 国服简历优化本地验收 — 20261018.1

> 后续修订：[20261018.2](cn-resume-optimizer-local-20261018.2.md) 已将页面精简、会员次数改为每日3次；本文件保留初版历史证据，当前规则以修订版为准。

状态：2026-10-18 国服版本地开发和自测已完成，23/23任务完成，尚未上线；未提交推送 Git。需求见[proposal](../../openspec/changes/add-cn-resume-optimizer/proposal.md)、[最终接口/金融合同](../../openspec/changes/add-cn-resume-optimizer/contract.md)、[36场景表](../../openspec/changes/add-cn-resume-optimizer/verification.md)。

## 已确定行为

国服中文简历优化支持自有ready简历及可选目标岗位/JD、有依据的参考评分/建议/待补事实、保守中文词句优化、原文/初稿/用户稿对照、revision安全编辑、真实Word/PDF和独立另存新简历。评分不代表录用概率，下载/另存需确认事实；标准模板不完全复刻原文件排版。

所有有效时间会员（含1天、周/月和已有管理员时间权益）按北京时间00:00每天免费1次，其他每次100积分，次数与模拟面试等功能独立。接受积分任务时实际扣100，失败/取消/超时/中断等未交付原路退还一次；完整成功后删除不返还。编辑、下载、另存不再收费，会员到期仍可操作自己未删完成稿。报价变化必须重新确认，不静默切付费；积分包不授予会员资格。

本轮只本地开发自测；国服线上、Global、助手和Admin服务不变。后续发布需要用户另行授权，重新核对实际镜像/配置/活跃用户门禁，不为发布结束用户会话。

## 实际组件基线与保护

- CN Backend：`sha256:4c305868ca6799cb7b8a69afd691f2e2e966785dfce827a0e04c51fa431fd656`。
- CN Web：`sha256:695959e95ef1ca20367c62333acd42e6aaf05df5c16692da039d8ca873cc0f2c`。
- 只读runtime source与bare image source共216项完全一致，完整OpenAPI195路径；不能使用混合Git目录、旧发布目录或健康版本字符串代替组件基线。
- worktree：`/Users/liyulong/.codex/worktrees/cn-resume-optimizer/offersteady`。证据在原仓库`artifacts/cn-resume-optimizer-20261018/`，仅脱敏源/清单/统计，无私有环境、用户正文或凭据。

独立完整应用probe已按最终冻结源重跑通过：原195路径和全部原component schema完全保留，新增7路径/9操作=202路径；完整源共228项，216旧输入中210项逐字不变，仅5个批准Python接入和依赖元数据变化，2337个旧函数AST保持，原Settings只增加CN开关/timeout两字段。真实DOCX/PDF最小签名通过，network/database/fileWrites/threadStarts/subprocesses/dependenciesResolved/lifespan七计数全零。证据`independent-full-app-probe.py/.json`；最终源清单SHA为`1e39f7a9e5d1b3120083a0b3889a9b51713b7153ded71923ae6c5ccc95db2f93`。Backend报告与独立probe的OpenAPI仅显式绑定的info.version不同，规范化该字段后完全一致；旧path/component均逐项核对。


功能源位于上述受管CN worktree。与Git HEAD之间还存在恢复实际CN区域基线带来的差异，不能将整个Git diff或整个dist目录直接当作本功能提交/发布包。本轮不做跨区域源码整合，Global独立worktree未修改，不提交推送Git。可复核API代码和本地自测完成不代表已制作可直接线上替换的整包。日后上线须重新核对actual drift，以批准增量/static overlay构建固定候选，私有配置留服务器，并重复保护真实活动用户的门禁；这是后续发布边界，不是本轮未完成开发任务。

## 格式和排版已执行验收

Root执行11项格式测试通过，4份合成真实文件含中文/中英混排、数字和联系方式；PDF1/3页、DOCX1/4页，共9页PNG由root逐页目视，无缺字、裁切、重叠，提取正文与末段完整。使用固定`reportlab==4.4.9`和OFL Noto CJK字体。字体SHA `fa2124fd2197ba2f050d48e1e66284d0aa00900657897eec679ab04d2913c429`，CN格式源SHA `ee7d2ea06403d44b7c05658b9e349696bded4ddadc688fca5a977cb8a497096d`。

证据`export-qa/verification.json`、`export-junit.xml`、`export-test-output.txt`。DOCX预览用isolated fontconfig加载OFL字体，其他reader可能替换字体；两格式内容一致，分页可不同。API鉴权、归属、revision、删除与重复导出的证据另外归入后端主套，不由格式渲染代替。

## 审查修正

1. 中文机构提取曾把“负责甲公司/承担甲公司”和“2020年加入甲公司/2020年入职甲公司”识别成不同机构，导致有依据改写误拒；已补最小前缀归一、4个中文合法改写及机构替换负例，最终主套通过。
2. 初版另存在共享billing-user锁内执行OSS慢I/O，可能阻塞同账号正常回答钱包准入。现锁序为global capacity→独立optimizer-owner→仅金融billing-user→source rows，另存/编辑不持wallet锁，保留revision/源删除屏障；真实PG阻塞另存回调时，旧reserve_usage/settle_usage仍完成，源删除竞态回归通过。
3. 新CN worker的空轮询与wake存在竞态，可能多等待一个3秒轮询周期；已将clear移到轮询前，并以确定性并发用例复现和验证。Global代码未修改。

## 最终本地验收

- Backend专用主套142项通过，0失败/跳过：金融24、服务/API41、Provider/eval58、受控表格19；真实本地PostgreSQL、受控供应商和独立执行器。证据`backend-verification/backend-verification.json`和`new-junit.xml`。
- 其后增加1项独立真实索引预留测试通过：旧BillingService索引预留120后可用80，正确拒绝100积分任务；原路释放后可接受，并验证重放/退款幂等。产品源及142主套源未变，证据`index-reservation-delta.json`及其JUnit。准确计数为142主套+1独立增量，不宣称143全集重跑。
- 国服Web456项通过（403适配旧基线+53新增，0失败/跳过），类型检查、正式模式构建通过。9份真实FastAPI/隔离PG响应进入客户端wire测试；无真实模型调用。
- Chrome宽1440/窄390像素32个检查点通过，错误0；全部绑定最终运行时源码。Chrome使用devVite，正式构建另外验证，不能称为直接运行生产chunk。合成预览中的附件只验证UI传输，真实DOCX/PDF内容和排版由上面的实际格式/API检查证明。
- Web236旧源中229逐字不变，7项批准增量，36旧顶层函数保留；本地构建83文件，入口`/assets/main-CPLgClq8.js`，SHA `e6c26b34e86340f15b1a6e1ce570a089b1e08796b175b302e5168197e0d68fbd`。证据`web-verification/candidate-proof.json`，该dist不是生产发布包。
- 33能力场景全部有对应本地证据；未来部署场景仅核对授权边界，未执行上线。OpenSpec严格校验、文档链接检查和最终源绑定完成。

[本地界面预览](http://127.0.0.1:5178/test-previews/resume-optimizer.html?scenario=free)使用合成账号/资料，不连接真实模型或线上账号。将查询参数改为`points`、`exhausted`、`balance`、`completed`可检查对应页面状态。预览不能代表真实模型优化效果，也不应将其中演示附件用于投递。

## 验收边界

所有资料为合成，模型为受控stub/MockTransport；没有调用真实生产模型、读取真实简历、创建真实面试/会员/收费任务或生产压测。自动事实校验只能检查指定可观察约束，无法证明所有中文语义真实性，仍须模型评测与用户核实。实体设备、真实模型质量、长期P95和生产用户验收未执行。

## 已执行的既有行为回归

Root在21个适用既有测试文件上完成313 passed、1 skipped、1明确deselected。唯一跳过`test_global_password_change_and_reset_keep_original_access_lifecycle`属于实际CN基线没有实现的Global专属生命周期；唯一排除`test_expiry_provider_error_is_lifecycle_event_with_private_diagnostics_hidden`断言的是未发布的Mock generation_stage日志。root在本轮新鲜冻结的完整实际CN旧源上独立复现同一失败，未修改旧runtime迎合测试。

证据`regressions/initial-{record,junit,output}`保留初次非零结果，`qualified-{record,junit,output}`保留适用集，`baseline-known-{record,junit,output}`是当前实际旧源复现；`baseline-only-differences.json`绑定旧Mock jobs SHA `73f11d55c05d0610fe251bb47467f4f5bb261a0ad8321287414f0b5f81a2b702`。不将skip/排除计通过，不宣称全仓全绿。

## 本地预览反馈修正

用户发现新增简历优化后看不到模拟面试。核查确认产品代码/路由未删，test-only预览把其他能力统一关掉而隐藏导航；这是验收遗漏。现显式恢复模拟能力、合成列表/报价/历史报告，普通刷新保留预览外壳，默认loopback API仅就地合成；正式disabled/error门禁保持。

新增4项真实App导航/门禁测试和3项预览handler测试，整体Web重新执行463/463通过、0失败/跳过，typecheck/build通过；83项生产模式构建文件中82项与原候选逐字一致，仅价格静态页由原构建流程重新生成，产品运行时代码未改。IAB实点优化→模拟面试列表→历史报告→优化、普通刷新→模拟，两个入口同时保留。独立复核实际CN基线16个Web及23个Backend模拟相关输入逐字一致。

原32项浏览器检查未覆盖同时导航，本次补齐该缺口；最终35场景、21/21任务。证据`web-verification/mock-preview-fix-proof.json`及`mock-preview-full-vitest.json`。预览明确仅合成演示列表/报告，不连接真实收音/助手、不创建真实面试或收费；线上未更新。

## 当前线上基线与纯新增范围复核（2026-10-18）

用户要求确认“以当前线上为基础，只增加简历优化”。本次通过既有SSH只读检查当前容器；前后端实际镜像、容器、启动时刻、重启数、Config/HostConfig/Mounts/Env摘要均与本轮开发基线相同，Backend216输入、Web294静态文件逐项SHA一致，NGINX一致，195原API和components完全一致。未发布/重启/写库，也未读取业务行或用户资料。证据`live-baseline-recheck-20261018.json`、`live-baseline-recheck-summary-20261018.json`、`current-online-additive-audit-20261018.json`。

后端直接取实际运行代码作为基线：210/216原文件不变，只有5个新功能接入Python与PDF依赖，原路由/schema保留；228完整候选源仍与独立验收清单相符。前端来自对应已发布源码快照及线上补丁核对恢复：236旧输入229不变、7项只增加简历入口/路由/资料入口/流水文案，原24条Route全部保留。未发现无关业务变更或删除。模拟面试、普通面试、笔试、收音、会员/支付及既有优化保持。

必须区分：后端是实际运行源码基线；前端NGINX镜像只有编译产物，恢复源码及本地83项构建并未证明与线上294项静态文件整体等价，不能把整个本地目录直接覆盖上线。未来授权发布仍应以届时实际镜像提取本功能最小增量，保留旧静态HTML/价格/媒体/NGINX和不可变资源。

“单独新增”指保留原业务规则并新增独立模块。它仍需接入原钱包/资料：新增两张优化表、精确扩展扣100/退100流水约束、删除源资料时同步清理优化稿；开启后有独立任务执行器并共享机器/数据库。因此不声称服务器资源或所有延迟绝对零变化。当前线上尚未应用这些变更。本次仅核对代码和证据，不重复无变化的测试，不新增产品行为。

## 复核发现的5项无关差异与修正

进一步独立审查确认，前述229/236是相对于恢复的源快照；该快照5项public内容与真实线上有差异，故原“没有无关变动”结论不应扩展到全部公共内容。现在已将llms-full.txt、public-facts.json、seo/features.html、seo/realtime-interview.html、sitemap.xml恢复为实际线上原字节，并核对生产模式构建后的5项逐字相同。线上从未部署这些差异。

新增5项固定线上SHA回归，在正确测试路径下复现5项SHA断言失败，再修正后整体Web468/468通过、0失败/跳过；build含typecheck通过。初次两份测试路径错误保留为harness报告，不计真实复现。原10个工作台产品运行时源不变。旧236基线和旧candidate-proof保持历史证据，最新为protected-baseline-files-current-20261018.json和current-candidate-proof-20261018.json，另存5项前后哈希及真实失败/通过结果。最终36场景、23/23任务。

当前能确认：Backend直接来自当前线上源；Web功能接入仅新增简历模块，已纠正无关公开内容。尚不能宣称整个恢复的前端源及83项dist与线上294项全量等价，不能直接整包覆盖。后续获授权发布应基于届时实际镜像构建最小增量，保留原公共页面、旧hash资源、50x和NGINX。新增功能会共享钱包、资料及机器资源；原功能和计费规则保留，不承诺绝对零资源开销。
