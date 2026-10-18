# 国服简历优化逐场景验收

状态：2026-10-18本地42场景及后续4项生产场景均已关联实际证据，当前共46项。第三次国服发布及独立verify完成；原本地记录保留，真实模型/正常用户生成质量仍待用户测试。

收费与事务以[最终合同](contract.md)为准；初次本地阶段不部署，用户后续明确授权国服上线后按[生产追加规范](production-release.md)完成发布；未提交推送 Git。

| ID | 能力 / 场景 | 状态 | 证据 |
| --- | --- | --- | --- |
| C01 | cn-grounded-resume-review-and-export / Review with and without JD | 本地通过 | provider tests: JD/no-JD/中文说明/服务器等权参考分 |
| C02 | cn-grounded-resume-review-and-export / Invalid review | 后端通过 | provider invalid-review/strict-score/HTTP失效案例；未交付金融释放 |
| C03 | cn-grounded-resume-review-and-export / Grounded Chinese wording improves | 通过 | test_real_chinese_rewording_is_allowed：4正例，包括机构/日期前缀 |
| C04 | cn-grounded-resume-review-and-export / Unsupported metrics or role upgrade | 通过 | test_unsupported_facts_are_rejected：数字/日期/机构/学历/技能/否定/责任升级 |
| C05 | cn-grounded-resume-review-and-export / Prompt injection in source | 本地Prompt/合成eval通过；真实模型未测 | 中文Prompt+16离线eval及MockTransport；不证明真实模型抗注入成功率 |
| C06 | cn-grounded-resume-review-and-export / Edit conflict | 本地通过 | draft revision/facts guards，stale保存拒绝且当前稿保留 |
| C07 | cn-grounded-resume-review-and-export / Download Chinese multi-page documents | 本地通过 | 11格式+9页root目视，edit_export真实双格式及表格export |
| C08 | cn-grounded-resume-review-and-export / Unauthorized or unavailable export | 通过 | foreign operations、revision/facts/unfinished/deleted源export、HTTP401/私有no-store |
| C09 | cn-grounded-resume-review-and-export / Save and reuse | 本地通过 | save_processing_ready真实Parser/Embedding路径ready，无新增优化/索引费 |
| C10 | cn-grounded-resume-review-and-export / Replay and later task deletion | 通过 | save-as replay同资料；删除task保留显式独立新简历 |
| C11 | cn-owned-resume-optimization-and-billing / General and targeted review | 本地通过 | general/targeted及owned-ready-JD真实版本，来源校验 |
| C12 | cn-owned-resume-optimization-and-billing / Invalid or foreign input | 通过 | bad_source参数组：foreign/version/deleted/processing/wrongkind/empty/oversize/markup，provider0/扣费0 |
| C13 | cn-owned-resume-optimization-and-billing / Controlled parsed table | 通过 | 19 source tests+controlled_table_same_source_quote_real_dual_export |
| C14 | cn-owned-resume-optimization-and-billing / Active members use today's benefit | 通过 | paid time1/7/30天+admin精确起止；与mock日额度独立 |
| C15 | cn-owned-resume-optimization-and-billing / Non-member or daily excess | 本地通过 | nonmember100/会员超额100/明确confirmPointsCharge，旧钱包真实扣后余额 |
| C16 | cn-owned-resume-optimization-and-billing / Midnight and prior-day release | 通过 | midnight replay/prior-day refund独立CN day，免费仅原日释放 |
| C17 | cn-owned-resume-optimization-and-billing / Free quote becomes stale | 本地通过 | quote changes never switch free to points；业务日/金额/确认字段严格 |
| C18 | cn-owned-resume-optimization-and-billing / Duplicate or conflicting idempotency | 通过 | 4并发同幂等键1job1charge、不同输入冲突、跨日/到期replay不重扣 |
| C19 | cn-owned-resume-optimization-and-billing / Insufficient funds or concurrent other spending | 本地通过 | 同wallet mock并发仅1成功；旧answer预留及独立真实BillingService索引预留120使available80并拒绝优化，释放/重放/退款均幂等；index-reservation-delta.json |
| C20 | cn-owned-resume-optimization-and-billing / Failure cancellation or recovery | 通过 | cancel/delete/source/failure/queue/lease原路退1次；退款注入故障整事务保留后安全重试 |
| C21 | cn-owned-resume-optimization-and-billing / Completion races cancellation | 通过 | completion_races_cancel金融终态一致且late finish不重扣/复活 |
| C22 | cn-owned-resume-optimization-and-billing / Completed result after membership expiry | 本地通过 | edit/export/save_no_additional_fee_after_membership_expiry |
| C23 | cn-resume-optimizer-isolation-and-verification / Disabled or another region | 本地通过 | disabled/wrong-region不构造model/repo/work，CN默认开关false |
| C24 | cn-resume-optimizer-isolation-and-verification / Full capacity or interrupted generation | 通过 | global_capacity_eight_single_running_ninth_nocharge、provider90s/queue15min/中断退款恢复不重放 |
| C25 | cn-resume-optimizer-isolation-and-verification / Interview workload is active in synthetic test | 通过 | real LiveAnswerStreamExecutor与CN Runtime独立容量及双方取消互不影响，合成无真实模型 |
| C26 | cn-resume-optimizer-isolation-and-verification / Foreign task operations | 通过 | foreign get/cancel/delete/edit/export/save均404，原owner内容/余额不变 |
| C27 | cn-resume-optimizer-isolation-and-verification / Source deletion races generation or save-as | 通过 | 源/JD删除阻止late delivery；save前删不创建、save先进行则delete等待且清空派生内容 |
| C28 | cn-resume-optimizer-isolation-and-verification / Processing disclosure and safe failure | 本地通过 | 固定ProviderError/no private payload、私有cache；最终中文UI披露及32浏览器检查点 |
| C29 | cn-resume-optimizer-isolation-and-verification / Repeat migration with an existing custom ledger kind | 通过 | migration customkind7保留，错误点数/旧sign拒绝，immutable update拒绝，重复迁移通过 |
| C30 | cn-resume-optimizer-isolation-and-verification / Compare candidate to bound runtime | 本地通过 | independent full-app guarded probe:216旧源/2337旧AST/195旧path及schemas保留，新增7/9到202 |
| C31 | cn-resume-optimizer-isolation-and-verification / Local verification is delivered | 本地通过 | 本地验收记录、最终Backend/Web/probe/格式/回归证据和33场景逐项核对；19/19任务，未上线 |
| C32 | cn-resume-optimizer-isolation-and-verification / Future deployment is considered | 范围核对通过；未执行未来发布 | contract/proposal/tasks明确本地交付；无部署/Git，未来门禁待另行授权 |
| C33 | cn-resume-optimizer-isolation-and-verification / Slow save-as and normal wallet usage | 通过 | slow_save_callback_never_holds_wallet_lock_and_old_spending_completes：真实旧reserve+settle在回调释放前完成 |

| C34 | cn-resume-optimizer-isolation-and-verification / Navigate between resume optimization and mock interviews | 本地通过 | 4项App真实组件回归+IAB列表/历史报告/返回优化；真实disabled/error门禁保留 |
| C35 | cn-resume-optimizer-isolation-and-verification / Refresh the synthetic preview | 本地通过 | 3项真实预览handler回归+IAB普通刷新仍保留两入口，禁止外部调用和真实创建 |

| C36 | cn-resume-optimizer-isolation-and-verification / Restored source contains unrelated public content drift | 本地通过 | 5个真实SHA失败复现→5项public源/dist均逐字对齐实际线上；整体Web468通过，current manifest/候选/差异证据保留 |

| C37 | cn-owned-resume-optimization-and-billing / Concurrent requests for the last free allowance | 本地通过 | 真实PG最后名额竞态只接受1个免费，另一409报价变化；原键replay不重占，重复cancel只释放1次 |
| C38 | cn-grounded-resume-review-and-export / A member starts a free optimization | 本地通过 | 精简默认表单/无费用大卡、明确AI同意、免费无支付弹层；PG前三次免费第四100 |
| C39 | cn-grounded-resume-review-and-export / Optional details and history are accessible | 本地通过 | JD/说明默认折叠可展开；tabs点击/键盘切换保留输入，空历史单独查看 |
| C40 | cn-grounded-resume-review-and-export / Paid start requires an explicit contextual confirmation | 本地通过 | 弹层100+余额+取消/Esc、余额99禁确认、stale重置；network/source/busy失败显示可访问错误，同键明确确认重试 |
| C41 | cn-grounded-resume-review-and-export / Existing result tools remain available | 本地通过 | 原评分/建议/编辑/WordPDF/另存/删除用例及最终Chrome结果页、4项App导航，Mock1次不变 |
| C42 | cn-grounded-resume-review-and-export / Narrow display keeps the main action usable | 本地通过 | 1440/390实际Chrome，表单/开始按钮/付费弹层无横向裁切；键盘tabs与Esc/焦点恢复 |

共 42 个能力场景（原36项及本轮6项）。

## 已核对的基线

2026-10-18 只读实际CN runtime与bare-image来源216项完全一致；完整OpenAPI195路径，旧账本两约束/唯一键清单已读取。独立记录：`artifacts/cn-resume-optimizer-20261018/independent-baseline-review.json`。此记录只证明基线，不代表候选、金融、自测、模型质量或上线验收。

## 未测边界

真实生产模型质量、用户会员真实生成流程、实体设备、生产压力/长期P95仍未执行。国服实际发布/独立验收已完成，见C43–C46；后续再次发布仍须其对应授权及实际基线/活动门禁。

## 已执行导出QA

Root于2026-10-18执行11项真实格式测试通过。4份中文合成文件包含中英混排、数字与联系方式，PDF1/3页、DOCX1/4页，共9页PNG已由root目视，无缺字/裁切/重叠，文本提取和末段完整。ReportLab固定4.4.9；OFL Noto字体SHA `fa2124fd2197ba2f050d48e1e66284d0aa00900657897eec679ab04d2913c429`；CN格式源SHA `ee7d2ea06403d44b7c05658b9e349696bded4ddadc688fca5a977cb8a497096d`。

证据位于原仓库 `artifacts/cn-resume-optimizer-20261018/export-qa/verification.json`、`export-junit.xml`、`export-test-output.txt`。DOCX预览使用isolated fontconfig加载OFL字体，其他reader可能替换字体；两格式内容一致、分页可不同。无真实模型、用户资料或生产写入。

## 已执行后端与既有回归

最终CN新增后端142项全部通过（0failed/skip/error），证据`backend-verification/new-junit.xml`与`new-test-output.txt`，真实PG与受控Provider，HTTP snapshot9个真实API响应、providerCalls0。源/Prompt/eval冻结在`candidate-proof.json`，独立审查`independent-code-review.json`无未解决阻断。

适用旧回归313passed/1Global-only skip/1明确排除；排除的未发布generation_stage日志断言已在本轮完整实际旧CN基线重现，初次非零/复现/适用集均保留。详见本地验收记录，不称全仓全绿。

最终完整app probe按已冻结源重跑通过：228项完整源，216旧输入全在/210字节不变，2337旧函数AST保持，全部原Settings只加2项CN字段，195原path及所有原components保留，7新path/9operations到202。七副作用计数零，没进入lifespan/模型/真实依赖；只有ReportLab4.4.9依赖新增。

## 最终Web及增量证据

Web最终456项（403旧基线+53新增）全部通过、0skip；typecheck/build通过，32个1440/390宽窄屏Chrome检查点绑定最终runtime源且error0，9份真实本地FastAPI/PG响应hash一致。证据`web-verification/candidate-proof.json`、`candidate-vitest.json`、`browser-final-checks.json`。Chrome为devVite呈现，正式构建另行验证；演示附件仅测UI传输，真实双格式见独立导出和API证据。

142后端主套后新增1项真实旧索引预留delta通过，产品/原测试源不变；共143个不同检查，未运行143项全集。记录`backend-verification/index-reservation-delta.json`与独立JUnit。

国服线上、Global、助手/Admin和Git未更新；本地dist及相对Git HEAD的区域恢复差异不能直接作为生产发布/提交包。最终19/19任务完成，33场景无未关联证据；真实模型、实体设备、生产压力/长期P95及真实用户生成效果仍未验证。

## 用户反馈：模拟面试入口在预览中消失

根因是test-only预览对其他capabilities统一返回disabled；原32项浏览器检查只覆盖新页面状态，漏测了既有模拟面试与新入口同时可见，不能作为该项通过证据。另补预览正常刷新外壳，避免刷新后落入没有合成配置的普通入口；默认loopback:8000 API请求也仅就地合成，不转发。

已增加4项真实App组件测试和3项真实预览handler测试；重新执行整体Web463/463、0失败/跳过、typecheck/build通过，83项正式构建文件中82项与前次候选逐字一致，仅价格静态页由原构建流程重新生成，产品运行时完全未改。IAB实点优化→模拟列表→历史报告→优化，并普通刷新、再次打开模拟，两个入口同时保留。只演示列表/报告，不创建真实面试或连接助手。原实际CN Web16个Mock相关文件及Backend23个Mock/语音/迁移/Prompt均逐字一致。

新增证据`web-verification/mock-preview-fix-proof.json`、`mock-navigation-regression.json`、`mock-preview-full-vitest.json`、`mock-preview-build.txt`、`mock-preview-restored.png`。本次不重跑无变更后端；未改线上、Global、助手/Admin或Git。新增2场景及2任务完成后为35场景、21/21任务。

## 当前线上复核与公共输入基线修正

只读SSH新鲜核对当前CN两个镜像/容器/配置/启动/重启均与开发冻结基线相同，216个后端源和294个Web静态文件逐字一致、195原API/schema一致。原Web229/236核对仅针对“还原源码基线”，不能据此声称全量线上一致。本次独立审查找到该快照5项无关公开内容差异，现已将llms-full/public-facts/seo-features/seo-realtime/sitemap恢复为实际线上原字节。

新增5-case固定线上SHA回归，正确路径下先复现5项SHA断言失败，再恢复最终源并执行全Web468通过/0失败跳过；生产模式build含typecheck通过、对应5项dist逐字一致。最初测试路径被Vite资源转换导致ENOENT的两份harness错误报告另存，不冒充缺陷复现；有效前后报告分别为public-static-before-vitest.json和public-static-final-vitest.json。旧manifest与旧候选证据不可改写，新current manifest以5项实际线上哈希修正，当前仍236输入229不变7功能接入。原10项产品运行时输入哈希不变；无须重跑无变化后端/模型/收音。

最新证据：current-online-additive-audit-20261018.json、web-verification/public-static-baseline-correction.json、current-candidate-proof-20261018.json、protected-baseline-files-current-20261018.json。前端仍为已发布源+线上补丁核对还原，不证明本地83项dist等价于线上全294项。后续发布须保护原HTML/价格/媒体/NGINX、50x和旧hash资源；本轮只修正本地基线，未上线/重启/写库/Git。最终36场景、23/23任务。

## 最新简洁页面与每日三次额度验收

本轮以用户最新确认为准：国服时间会员每个Asia/Shanghai自然日免费3次，非会员及超额100积分，仅实际付费开始前弹层确认。主页面移除顶部费用/余额/重置大卡，紧凑单列表单和独立历史tab，JD/处理使用说明默认折叠，保留明确AI处理同意和所有结果操作。

真实本地PG全部147/147通过（原143合并本轮4新增；金融28、服务41、索引1、provider58、source19），0失败/跳过，前三个成功结果免费、第四100，最后名额竞态/原键/取消/跨日/原日退还通过。原Mock源码与实际CN基线逐字相同且仍1次，Global/Prompt/导出格式模块未变。新9响应wire与Web副本SHA相同，providerCalls0。

Web全套480/480、0失败/跳过，typecheck/production build通过；59项针对性是全集子集，不额外相加。Chrome1440/390共10个最终检查，默认视图/键盘/历史保留/免费完成/付费确认取消Esc/余额不足/报价变化/原模拟导航/刷新通过，console error0。Chrome使用devVite，不是正式chunk直接验收；演示输出和导出附件仅合成样例，原真实格式验收保持先前证据。本轮首次全Web通过后仅修正演示JD字段/匹配标记，并重新跑最终完整480项；早期完整结果另存。

独立审查发现付费失败时弹层遮挡页内错误P2，已对全部create错误关闭弹层并恢复可用主按钮焦点，保留幂等键和再次明确确认；network/source/busy三例回归通过，无剩余P1/P2。最新16个Web输入已冻结，旧236输入仍229不变7功能接入；相对上个已验收候选仅Page/CSS两个产品输入改变，Backend仅3个CN optimizer输入调整，原功能保护不变。5项已对齐public源/dist仍逐字相同。

证据：原仓库`artifacts/cn-resume-optimizer-20261018/ui-refresh/verification.json`、`backend-verification.json`、`backend-junit.xml`、`web-vitest.json`、`web-build.txt`、`web-typecheck.txt`、`browser-checks.json`及desktop-simple/mobile-simple/mobile-payment截图。正式构建83项，入口main-DAkdVewn.js；整个dist仍不是生产替换包。27/27任务、42场景，本地预览已刷新；必须等用户本地确认后另行授权才上线，本轮无生产或Git操作。

## 2026-10-18 用户批准生产发布追加（待执行）

用户已明确授权将已验收的 20261018.2 上线国服，遵循[生产追加规范](production-release.md)。上述42项和“未上线”描述保留为本地交付历史，不能代替本次实际生产结果。新增3个生产场景，当前共45项；新项须依真实发布证据更新。

| ID | 能力 / 场景 | 状态 | 证据 |
| --- | --- | --- | --- |
| C43 | cn-resume-optimizer-isolation-and-verification / Authorized candidate is prepared and verified | 第三次实际候选准备及独立核对通过 | production-prepare-v3.json固定Backend995ae331…/Web20d6a03a…；production-candidate-probe-v3.json：228源/202完整路径、原195路径及schema保留、真实合成DOCX/PDF、七类副作用0；independent-actual-candidate-audit-v3.json核对实际候选与本地冻结输入，不代替上线验收 |
| C44 | cn-resume-optimizer-isolation-and-verification / Protected work appears before cutover or recovery | 控制器回归及实际门禁/保护恢复通过 | 86控制器合成回归含活动/未知/读失败/归属/部分发布/新用户阻止恢复；production-final-idle-gates-v3.json全部7门禁退出0、保护字段0，容量样本24.563秒；production-restored-snapshot.json记录第二次按相同门禁/固定镜像Web→Backend恢复；没有终止用户或清理记录制造空闲 |
| C45 | cn-resume-optimizer-isolation-and-verification / Production verification completes without real user generation | 第三次实际发布/独立verify/短时统计通过 | production-deploy-v3.json和production-verify-v3.json同固定新容器/镜像995ae331…与20d6a03a…；7公开GET200且HTML/build SHA正确，2匿名API401/private,no-store；production-migration-v3.json旧trigger/其他约束保留、无历史行修改；新Backend148秒/Web114秒ERROR/traceback/HTTP5xx均0，其他组件/配置保持；independent-final-release-audit.json独立逐项核对，无真实模型/扣费测试 |

## 公开文件权限发布回归（第三次尝试前）

新增C46，当前总计46场景。第二次生产发布确已迁移/切换后公开验收HTTPError失败（原异常未保存路径/状态），随后同固定候选隔离六路径403并确认公开文件0600，推断原失败与该权限缺陷一致；已按活动门禁/归属恢复固定旧镜像；不能沿用此前“未执行生产发布”的历史表述作为当前状态。第三次实际候选已通过准备、权限与隔离HTTP验证（见C43/C46），本次生产切换、独立verify及短时脱敏统计现已通过（见C44/C45），此前失败/回退证据完整保留。

| ID | 能力 / 场景 | 状态 | 证据 |
| --- | --- | --- | --- |
| C46 | cn-resume-optimizer-isolation-and-verification / Private staging permissions must not cause public HTTP failures | 第三次实际候选修正及隔离验证通过 | v4权限缺陷原证据保留；86控制器回归、installer同AST在umask077验证、production-web-public-mode-probe-v3.json以nginx用户读取17新路径通过；isolated-nginx-routes-v5.json固定Web20d6a03a…真实17GET（6应用/标识+11资源）全部200/预期SHA，index/config0644，NGINX正确，隔离实例已删除；未用生产用户/模型 |

第三次候选独立审查：`independent-actual-candidate-audit-v3.json` 将实际 prepare 镜像与隔离 NGINX 镜像绑定，逐项重新计算17个响应预期SHA，并核对完整OpenAPI候选SHA及七类副作用0。C43/C46先完成候选验证；随后C44/C45依真实切换、verify和短时统计证据完成，任务状态由root据同一证据更新。

## 国服实际发布最终独立核对

第三次发布于北京时间2026-10-18 04:14:12.465完成，04:14:54.740独立verify通过。Backend容器4667f8b8…运行995ae331…固定候选，Web容器029e84e0…运行20d6a03a…固定候选；deploy与verify身份一致。7个公开GET200（健康、登录、构建标识、简历优化、模拟面试、普通面试新建、笔试），除动态健康外HTML/构建正文SHA逐项等于冻结候选；2个匿名优化API均401且private,no-store。

最后完整7门禁保护计数0，旧历史失败资料7项仅信息计数，未删除；旧钱包trigger/其他约束保留，无历史账本行修改。配置仅新增CN专属开关，非目标组件保持。短时统计请求窗口180秒，但新容器实际覆盖Backend148秒/Web114秒，各ERROR/traceback/HTTP5xx均0，不能称完整180秒新容器观测或长期性能验收。独立校验脚本/证据为本次发布artifacts下`independent-final-release-audit.py/.json`。

真实用户正常生成、模型优化质量及长期资源/延迟表现仍由用户测试；发布验收未代用户调用真实模型、创建面试或扣积分，也未推送Git。第二次实际切换/公开HTTPError与保护性回退事实保留，不能据最终成功宣称全程没有线上影响。

## 2026-10-18 失败定位本地修复验收

追加7项本地场景，总计53项；此前生产版本的46项事实保留。本次未发布，旧invalid_output的具体历史原因不能还原。完整回归283通过、0失败/错误/跳过；输入SHA及JUnit在`artifacts/cn-resume-optimizer-failure-20261018/local-hotfix/verification.json`，独立审查在`artifacts/cn-resume-optimizer-20261018-failure-diagnostics/independent-audit/`。

| ID | 能力 / 场景 | 本地状态 | 证据 |
| --- | --- | --- | --- |
| C47 | cn-grounded-resume-review-and-export / A valid JSON review has only transport wrapping | 通过 | 新Provider包装等值正例、16条兼容eval；原16条事实eval经BOM/json围栏复测；原Prompt不改 |
| C48 | cn-grounded-resume-review-and-export / Ambiguous or damaged model content | 通过 | 说明、多对象、多围栏、重复key含嵌套、非法/截断、非stop、NaN/Infinity/浮点溢出负例；无修补或自动重试 |
| C49 | cn-grounded-resume-review-and-export / Wrapped fabricated content remains invalid | 通过 | 新/原事实eval全部经相同引用、数字、实体、责任及其他守卫；五函数AST仅固定reason变化 |
| C50 | cn-owned-resume-optimization-and-billing / A diagnosed failure is persisted and replayed | 通过 | 真实隔离PG积分/免费同事务失败诊断与一次释放、重复回调、强制SQL故障回滚；原收费和原日释放保持 |
| C51 | cn-owned-resume-optimization-and-billing / A later failure arrives after cancellation or source deletion | 通过 | 取消/任务删/源删迟到失败false、不复活payload、不重复退款及无失败日志；租约过期存储/日志均interrupted，旧无原因记录兼容 |
| C52 | cn-resume-optimizer-isolation-and-verification / A user can distinguish a model validation failure | 通过 | owner固定中文errorMessage；新failed+released才附退款；9份HTTP响应键/类型结构与旧合同相同，诊断不出wire，旧fixture SHA不变 |
| C53 | cn-resume-optimizer-isolation-and-verification / Untrusted content cannot enter diagnostics | 通过 | 固定34原因allowlist、伪pair/额外字段/隐私哨兵拒绝；异常和JSON日志不带原文/身份；原权限回归及独立8运行时组合通过 |

本地交付细节和限制见[20261018.3本地修复记录](../../../docs/releases/cn-resume-optimizer-local-20261018.3.md)。没有真实模型、用户任务重放、生产切换或Git操作；283项通过不能改写历史失败为已解决。

## 2026-10-18 失败诊断热修复生产追加（已完成，初始计划保留）

用户最新已明确授权继续优化后上线，并许可一次纯合成真实Provider定位。遵循[热修复生产规范](hotfix-production-release.md)，新增4场景，总计57项；9.x本地53项及旧生产版本事实保持。本节初始待执行计划及后续尝试记录保留；当前全部结果见末尾最终独立验收，不用本地283通过代替真实候选/模型/切换证据。证据统一保存原仓库`artifacts/cn-resume-optimizer-hotfix-20261018-release/`；[热修复发布记录](../../../docs/releases/cn-resume-optimizer-hotfix-20261018.1.md)据后续真实证据更新。

| ID | 能力 / 场景 | 状态 | 所需证据 |
| --- | --- | --- | --- |
| C54 | cn-resume-optimizer-isolation-and-verification / The four-file candidate is tied to the actual Backend | 新dir2实际候选及独立核对通过 | 实际固定Backend/228源/202完整路径schema/配置与非目标重新冻结；四文件229候选/控制器/七门禁SHA；真实禁网只读无生命周期探针及控制器合成回归 |
| C55 | cn-resume-optimizer-isolation-and-verification / A hotfix meets protected activity or unavailable gate | 合成回归及实际七门禁通过 | 60控制器回归含活动/未知/读失败/归属/恢复；实际preflight和切换前重复7门禁exit0/保护0，容量样本23.508秒；旧7失败任务仅信息、不清理，dir1真实摘要漂移被拒绝，未终止用户 |
| C56 | cn-resume-optimizer-isolation-and-verification / Owned Backend release is accepted or safely recovered | 实际发布及独立verify通过，未触发回退 | deploy/verify-v2同b955…/6f2a…；229源/202schema/340Settings/7非目标/305静态原配置保持，7公开200及原HTML/build SHA、2匿名401/private,no-store；Backendhealthy重启0，短时107.969/87.266秒各ERROR/traceback/5xx0 |
| C57 | cn-grounded-resume-review-and-export / One synthetic Provider check gives a bounded release decision | 一次真实纯合成Provider通过 | 请求1次19335ms，4维/5建议/6待补/806字符，守卫通过；marker/receipt与candidate6f2a…/4源码/script/contract/case/input e6c6…完全绑定，未额外重试/改Prompt/放宽事实，不建job/账本/真实资料 |

## 挂载数组顺序工具修正追加（待确认与验收）

首次热修复preflight因non-target摘要差异停止，未模型调用或切换。PG Mounts完整原值是否仅排列尚待服务器只读核对；旧候选验收及停止证据保留，不能称PG实际挂载改变。新增2场景，总计59项，遵循[窄规范](hotfix-production-release.md)。

| ID | 能力 / 场景 | 状态 | 所需证据 |
| --- | --- | --- | --- |
| C58 | cn-resume-optimizer-isolation-and-verification / Only the Docker mount inspection order changes | 通过 | 服务器全字段多重集/原始摘要排列复现，Mounts仅最外层完整canonical排序，合成排列等价回归；新dir2实际重新freeze/prepare/独立探针 |
| C59 | cn-resume-optimizer-isolation-and-verification / A mount field or multiplicity actually changes | 通过 | 任一已有/未知字段或条目增删/重复数量变化仍拒绝，HostConfig/其它保护不放宽，旧停止和prepared证据保留 |

尝试1实际结果：`production-prepare.json`及`actual-candidate-evidence.json`/`actual-candidate-review.json`证明候选6f2a53f5…/229源/202路径和七副作用0；`production-preflight.json`记录停止，`non-target-drift.json`仅为安全摘要差异。此处不提前声称排序原因已确认或修正发布已完成。

挂载核对后续更新：`mount-order-proof.json`已证明7非目标完整条目多重集相同，PG两条的稳定排序摘要229772…恰复现preflight差异，原序d6d61…仍可复现。该证据只确认C58中的只读事实部分；controller-v2的排列等价/字段及增删重复拒绝回归、v3基线和新dir2实际prepare尚待审查。C58/C59当前不提前标全部通过，10.2重新pending。v3 SHA00e57147…除atMs与PG稳定mountsSha外无其他字段变化，Source/Destination/RW/完整HostConfig等保护不减少。

新dir2实际候选证据更新：C54由actual-candidate-evidence-v2.json/actual-candidate-review-v2.json和production-prepare-v2.json完成；完整229源/202路径/2f030c…schema、Config/父层、真实合成格式及七副作用0均与e5ad4d31…控制器和e6c6bc42…输入绑定，原Backend仍在运行。C58由mount-order-proof.json、v3新基线00e57147…、完整canonicalMounts和新实际prepare/preflight通过；C59由60项控制器回归中新增15项字段/条目/重复/嵌套/HostConfig保护及独立10项检查完成。仅Mounts最外层排列规范化，真实变更仍拒绝。10.2重新完成；C55–C57和10.3–10.5须后续门禁/Provider/切换/验收实际结果，不据本段提前通过。

## 热修复生产最终独立验收（59场景、41任务完成）

dir2于北京时间05:07:33.546仅Backend切换，05:08:35.669独立verify通过，实际新容器b955c33e…/6f2a53f5…同部署/探针/一次Provider绑定。controller e5ad4d31…、input e6c6bc42…、基线00e57147…全部重算相符。完整最终七门禁均exit0/保护0，容量样本23.508秒；旧7失败资料信息计数不清理。229源/202完整schema/340Settings和有效环境、7非目标、305旧静态/NGINX保持；Backend IP未变，无代理刷新或非目标重建。C54–C59均按上述真实或合成证据完成。

实际纯合成直接Provider只调用1次，19335ms，结构/依据/事实校验通过；不创建生产job/usage/钱包/资料或面试，没有真实用户内容夹具、额外模型重试、Prompt/费用/DDL/环境变化。7公开GET200的HTML/build SHA与原冻结静态逐项相同，2匿名接口401/private,no-store；Backend运行/healthy/重启0。最终短时观察Backend107.969秒、Web87.266秒，ERROR/traceback/HTTP5xx均0、固定诊断聚合空/未知0、未截断、不导出原始用户日志。该结果不代表完整180秒或长期P95，不恢复原用户旧失败细项或证明其任务已成功。

独立可复算证据：本次发布artifacts中`final-release-audit.py`及`final-release-audit.json`、`production-final-safe-evidence-v2.json`、`production-deploy-v2.json`、`production-verify-v2.json`、`production-short-observation-v2.json`、`production-provider-check-v2.json`。dir1 preflight停止和完整Mounts顺序证明、旧prepared包保持，未以新成功覆盖失败历史；无Git/Global/助手/Admin或Web重建。本阶段验收完成，用户正常账号/原简历真实体验由后续自测验证。

## 2026-10-18 11.x明确本地开发授权与当前验收

用户已明确要求按讨论点开发。现[精确合同](safe-edit-application.md)增加逐edit安全选择、无有效修改失败退款和公开安全计数，取代此前11研究的原限制；旧41任务及59场景的历史证据保持；root随后已完成11.1 strict实施GO，11.2–11.4据本地证据完成，11.5/11.6待对应实际验收。新问题事实仍为3437字/noJD、28030ms、fact_english_content_added且全退，实际新增词未知，Web漏显示原因已证实，禁止用户正文/原模型响应夹具。本轮仅本地开发/自测/预览和有界隔离合成QA，不生产切换。

新增14个产品场景及2个QA工具故障回归，合计75；状态只据本轮证据，不据旧283通过或先前单例模型成功提前完成。

| ID | 能力 / 场景 | 状态 | 计划证据 |
| --- | --- | --- | --- |
| C60 | cn-grounded-resume-review-and-export / Valid edits survive independently rejected proposals | 本地通过 | 393去重后端含22项真实隔离PG/API：partial仅安全稿completed/settled一次，拒绝正文不入payload/wire/logs；独立core审查 |
| C61 | cn-grounded-resume-review-and-export / Global review errors still reject the whole result | 本地通过 | 最终新Provider88/42 AIeval覆盖全局JSON/schema/评分/evidence/语言/限长/最终稿失败，不交付部分稿 |
| C62 | cn-grounded-resume-review-and-export / All overlapping qualified edits are excluded independent of order | 本地通过 | Provider合格候选全相交/链式/邻接/输入重排覆盖，全部参与者剔除、顺序独立 |
| C63 | cn-grounded-resume-review-and-export / No effective edit fails and prioritizes a real rejection | 本地通过 | empty/noop/最终无变化/首非noop/overlap；22项真实PG/API验证free/points原子一次释放与故障回滚 |
| C64 | cn-grounded-resume-review-and-export / Meaning comparison cannot loosen fact checks or rewrite content | 本地通过 | canonical仅变化检测；原20事实/parser AST及generate不变，P2边缘control修复独立12例保留其余safe |
| C65 | cn-grounded-resume-review-and-export / Safe edit counts describe proposals without rejected content | 本地通过 | 新summary服务端互斥计数及方程；Web572含真实wire和恶意meta，拒绝正文/位置/reason不外露 |
| C66 | cn-grounded-resume-review-and-export / Old completed results and user revisions stay compatible | 本地通过 | 真实PG旧v1无summary读/编辑/导出；Web初稿摘要不随用户保存改变、不重费 |
| C67 | cn-grounded-resume-review-and-export / Malformed edit summary metadata is hidden instead of guessed | 本地通过 | Web572含未知key/类型/范围/方程/applied0/非completed隐藏，真实wire/Page新4例通过 |
| C68 | cn-grounded-resume-review-and-export / CN v2 preserves content words inside each source quote | 本地通过；真实模型待验收 | v2Prompt/42纯合成AIeval同quote原词/格式/借词正反；原v1/schema/事实守卫保持，3真实QA尚未完成 |
| C69 | cn-grounded-resume-review-and-export / New v2 tasks do not rewrite historical v1 results | 本地通过 | 新任务v2及真实PG构造旧v1无meta编辑导出，未回填历史 |
| C70 | cn-grounded-resume-review-and-export / The compiled failed page shows an allowlisted local explanation | 通过 | web/browser-verification.json：实际compiled IAB新建轮询/历史no_effective原因、Chrome已知事实原因，权威原日/100积分退还独立可见 |
| C71 | cn-grounded-resume-review-and-export / Unknown private or inconsistent error messages stay generic | 本地通过 | helper精确code/本地常量及released后缀，unknown/private/HTML/对象/拼接/误形code回退；root独立审查 |
| C72 | cn-resume-optimizer-isolation-and-verification / Local development preserves the frozen live product | 通过 | source-and-backend-verification.json、393不同Backend/572Web、13实际IAB/Chrome观察点、315静态保留/原Mock报告；仅本地开发不切换 |
| C73 | cn-resume-optimizer-isolation-and-verification / Three synthetic provider cases remain bounded and isolated | 通过 | qa/actual-case1/2/3-v2.json及actual-verify-v2：3固定约3k合成例各1请求，5/7/5实际有效改写，七门禁/marker/230输入绑定；不生产任务/钱包或重放用户 |
| C74 | cn-resume-optimizer-isolation-and-verification / A proven pre-start mount failure keeps the consumed attempt | 通过 | first-attempt-safe-diagnosis.json确认runc init前进程/请求0，旧marker保留；actual-prepare-v2 Linux单目录case SHA演练、26工具回归和qa-actual-v2独立审核通过，实际请求总3 |
| C75 | cn-resume-optimizer-isolation-and-verification / A synthetic case uses one verified read-only directory mount | 通过 | first-attempt-safe-diagnosis.json确认runc init前进程/请求0，旧marker保留；actual-prepare-v2 Linux单目录case SHA演练、26工具回归和qa-actual-v2独立审核通过，实际请求总3 |

研究安全元数据与14词规则合成例保留为研究证据，不能代替新算法/金融/浏览器或3例QA通过。root新实际基线证据为artifacts/cn-resume-optimizer-safe-edits-20261018/current-baseline.json（08a10e80…）；本次新验收与记录使用该独立目录，不覆盖10.x发布/停止/一次模型记录。


11.6当前工具事实：dir1 actual-prepare.json通过candidate912137e93da3635a7f63d39610329095bd27035601c7e7e709177e8cba835a6d；actual-case1.json只返回synthetic_provider_probe_incomplete。服务器原stderr未导出，固定安全分类first-attempt-safe-diagnosis.json全部预启动检查为true，containerProcessNotStarted=true/providerRequests=0/consumedMarkerPreserved=true/laterCasesStarted=false/productionSwitched=false。不将其写成模型无效输出、产品失败、真实QA已通过或上线。只按[合同第9节](safe-edit-application.md#9-qa预启动挂载故障的窄修正不改变产品或模型预算)修QA工具、另dir2重冻后root复核；未知或可能已请求时不得恢复。本轮实际请求预算仍<=3，11.6保持pending。

11.x最终本地交付：393不同Backend案例、572Web及类型/生产build、42新AI eval/22真实PG/API、13实际compiled IAB/Chrome观察点、1003 HTTP断言与3长合成真实模型各一次均按新增证据通过。75场景对应证据齐全，47任务完成；当前无本轮生产切换/Git/Global/助手/Admin变化。三例实际只过滤2项unchanged；事实违规partial由本地负例证明，不夸大模型采样覆盖或用户原任务成功。

## 2026-10-18 用户授权安全局部改写生产追加（12.x已完成）

用户已明确要求部署上线，采用[12.x生产规范](safe-edit-production-release.md)。既有47任务/75场景及final-verification SHA dc869f66…历史保持；新增5任务和6场景现由dir3实际证据覆盖，合计52/52任务、81场景。生产忙碌/回退未发生，条件分支只以合成回归覆盖。

| ID | 能力 / 场景 | 状态 | 实际证据与边界 |
| --- | --- | --- | --- |
| C76 | cn-resume-optimizer-isolation-and-verification / Refreeze actual CN components before safe-edit release | 通过 | current-baseline.json SHA5a670a02…实际6f2a/20d6、229/202/340/305/配置非目标与root-v3-go完整绑定 |
| C77 | cn-resume-optimizer-isolation-and-verification / Safe-edit candidates pass isolated backend and NGINX probes | 通过 | actual-prepare/evidence-v3：f6/2124、230/202/schema/真实DOCXPDF/七副作用0；306/316精确模式及25隔离HTTP/SHA/清理；两次停止历史保留 |
| C78 | cn-resume-optimizer-isolation-and-verification / Protected work defers every safe-edit switch or recovery | 通过 | 实际preflight与逐步七门禁均有效空闲，最后sampleAge24945ms；busy/unknown/readfail停止由115工具测试验证，线上未等待或清理活动 |
| C79 | cn-resume-optimizer-isolation-and-verification / Ordered safe-edit cutover resumes without duplicate restarts | 通过 | actual-deploy/runtime：Backend→Web、50bcb/88ae固定归属、重启0；部分恢复由合成测试，线上未部分发布或代理reload |
| C80 | cn-resume-optimizer-isolation-and-verification / Owned safe-edit rollback preserves users and data | 通过 | 115工具测试覆盖固定恢复/新活动门禁/归属拒绝/未知停止；实际无回退/DDL/测试钱包写入，旧发布与QA证据保持 |
| C81 | cn-resume-optimizer-isolation-and-verification / Independent safe-edit acceptance reports actual deployment scope | 通过 | actual-verify/runtime/evidence/observation-v3及final-release-review：230/202/340/315/6非目标共享tag，19HTTP=17x200+2x401，114.289/79.385秒未截断零错误，无额外模型 |

证据目录artifacts/cn-resume-optimizer-safe-edits-20261018-release/，实际服务器归属dir3；[生产记录](../../../docs/releases/cn-resume-optimizer-safe-edits-20261018.1.md)现已完成。正式build仅.local改.1，其余14patch/10JS保持，无额外模型。下两段为首轮停止时历史，最终以本节表格及末段为准。

12.1只读基线部分已取得：root新生产冻结证据artifacts/cn-resume-optimizer-safe-edits-20261018-release/current-baseline.json，SHA5a670a02c4484dde6d01056ed1908aa3edb0680ee80df52db412add3043e748a；除atMs外与已验收QA基线每个完整字段相同，实际229源/202schema/340Settings/305静态/NGINX/全部非目标、Backend healthy/重启0保持。此事实只完成12.1的基线部分，root独立strict实施GO尚待记录，12.1暂不勾选，不代表候选/发布完成。

12.x首轮prepare在candidate_public_file_permissions_failed停止，未切换/未调模型。actual-public-mode-diagnostic.json证明316全部可读；actual-baseline-public-modes.json SHA ae9835e7ebdfa2c449c38f06fc5cf7281249edd5c88b773051020908a78777bb证明旧20d6精确同8元数据755、其余原/NGINX644及10目录755。C77/12.2待执行，新dir2仅修精确模式probe，固定Web2124eee8…/Backendf6重新全部实际验收；dir1失败/候选历史保持，不称实际权限/NGINX或上线已通过。场景总数81不变。

最终dir3独立验收通过：控制器c6dce7b3…/input9aa65c2d…，Backend50bcb76f…/f6与Web88ae70c9…/2124在deploy/verify/完整快照中一致，Backend healthy、重启0。两次线上各19检查通过；Backend114.289秒404行、Web79.385秒179行均未截断，ERROR/traceback/5xx/固定失败/未知诊断全0。dir2因internal网络publish为空在HTTP前TypeError停止，25HTTP内存私有IP诊断及dir3正式探针修正保留；两次prepare停止均未切线上。无新模型、真实测试任务/钱包、Git/Global/助手/Admin重建；不代表长期P95或原用户简历已成功。
