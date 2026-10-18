# CN Resume Optimizer contract v2 (local UI/quota revision)

2026-10-18 root 已批准本合同，状态 apply-ready。初次范围为国服本地开发自测；2026-10-18 用户已另行明确授权将验收版本上线国服，发布遵循 [生产追加规范](production-release.md)，仍不提交推送 Git；worktree `/Users/liyulong/.codex/worktrees/cn-resume-optimizer/offersteady`。

## 基础语义与区域隔离

公共前缀 `/api/v1/resume-optimizer`，认证CN账号、owner由服务端推导。端点/原wire/limits/任务/权限/删除/编辑/另存/导出语义复用 [Global合同](../add-global-resume-optimizer/contract.md) 的对应段落，下列CN差异优先。新模块`cn_resume_optimizer_*`、表`cn_resume_optimizer_jobs`/`cn_resume_optimizer_usage`、迁移`0054_cn_resume_optimizer.sql`，开关`cn_resume_optimizer_enabled`默认false，CN且模型/开关有效才执行。Global表/开关/UTC会员专用政策保持。格式模块由root维护`app.services.resume_optimizer_export.render_resume_export`。

## 金融与锁

- 有效时间会员来自`billing_time_pass_entitlements`或`admin_time_entitlements`的当前active/starts<=now<ends，含1天/周/月/管理员时间权益；纯积分包不授予会员。
- Asia/Shanghai自然日独立3免费，daily_pass_free reserved/settled占当日；points不占free，非会员及超额100积分。
- 锁顺序固定为全局optimizer capacity（需要容量时）→独立`cn-resume-optimizer-owner:{owner}`→`billing-user:{owner}`（仅金融操作）→source rows。所有优化状态读写使用同一optimizer-owner锁，创建/完成/失败/取消/恢复/清理等金融变化再持既有billing-user锁；已完成稿的编辑/另存不持wallet锁执行OSS/Parser I/O，仍保留source shares、revision和删除屏障。job、usage、免费占用或实际-100不可变`resume_optimizer_charge`必须同连接/事务。可用余额=旧账本总和减旧回答/索引reserved，新usage reserved只表示未交付，不再减一次钱包。创建扣除使旧消费者立即看到扣后余额。
- 完整有效结果与usage settled同事务，不二次扣分。失败/取消/源删/超时/排队过期/重启使未交付时，同事务原日free释放或唯一+100`resume_optimizer_refund`且released。创建和退款reference唯一，完成/取消条件屏障，回调重放不重扣/退。completed删除/取消/导出失败不返还。
- 迁移动态读取旧kind/points约束，只精确OR新两kind和-100/+100条件，保留全部旧合法/未知扩展kind、符号限制和immutable trigger；缺失旧约束fail closed，禁止静态名单覆盖。仅2新表及必要约束，不改历史账本。
- 编辑/读/下载/另存未删完成稿不再收费，会员到期仍可操作。

## GET capabilities

保留Global基础字段，CN新增/差异：`eligible=true`（已认证账号可进入）、`memberRequired=false`、`activeTimeMember:boolean`、`dailyLimit:3`、`dailyRemaining:0|1|2|3`、`quotaDay:YYYY-MM-DD`、`timezone:Asia/Shanghai`、`resetAtMs`、`nowMs`、`billingClass:daily_pass_free|points`、`entryPoints:0|100`、`availablePoints:int`、`canStart:boolean`、`activeJobId:string|null`。`exhausted`仅会员当日free用完/占用，仍可付费；非会员dailyRemaining0/points100。canStart至少要求enabled、无个人未完成且free或available>=100，容量由服务端权威检查。读取能力不预留、不初始化/调用模型。全部私有JSON/附件private,no-store。

## POST jobs

沿用Global source/JD/targetRole/idempotency/confirmProcessing，`quotedQuotaDay`为CN业务日；新增必填`quotedBillingClass:daily_pass_free|points`、`quotedPoints:StrictInt`只许0/100（拒绝bool/string/float），`confirmPointsCharge:StrictBool=false`，points必须true，free可省；confirmProcessing必须true。

缺字段422；日期/当前模式/费用/权益变化409`resume_optimizer_quote_changed`，不可复用旧确认或自动切付费；余额不足402`resume_optimizer_insufficient_balance`；付费未确认422`resume_optimizer_points_confirmation_required`。其余沿用固定resume_optimizer_*错误，消息中文，不使用Global会员403/超额429政策。

Fingerprint只绑定逻辑输入，排除idempotencyKey/全部quoted字段/confirmPointsCharge/confirmProcessing。匹配replay先返回原job，跨日或会员/现价变化不重扣；不同输入conflict。输入/容量校验在金融改变前，任何创建失败整事务回滚。不调用MockRepository独立事务。

## Wire与中文事实边界

JobSummary新增`billingClass:daily_pass_free|points`、`pointsCharged:0|100`（原接受金额不因退款改历史）、`billingStatus:reserved|settled|released`；原`allowanceStatus`同状态兼容。quotaDay为CN，promptVersion中文专版。其余Global字段形状不变。

中文解释/建议/待补事实，源引用和事实稿保持源语言。独立中文Prompt/evals；保守唯一sourceQuote局部替换、非重叠并保留未编辑段落；允许真实中文动词/句式优化，例如“负责使用Python开发数据接口”→“使用Python实现数据接口开发”，不得逐字锁死全部中文而仅改排版。数字/中英文日期/联系方式/URL/Latin技术、常见中文机构学历技术、否定和参与→主导/独立责任升级守卫，加中文正负eval和用户事实确认；静态规则不能证明全部语义真实性，JD内容不能变候选人事实。缺失信息只待补充。

沿用每owner1unfinished、全局8unfinished/1provider、90s超时/15minqueue，独立执行池。受控HTMLParser规范化输入副本，未知markup收费前拒绝，原文件/Parser/旧面试快照不变。DOCX/PDF真实中文统一模板、字体许可/多页QA，private附件。源删同事务清理和迟到屏障、revision、事实确认、另存独立资料基础语义沿用Global，金融和锁改CN策略；另存的非金融慢I/O不阻塞同账号普通钱包准入。

## 简洁页面报价交互

服务端仍权威返回完整报价与Asia/Shanghai重置字段，主页面不必常驻展示。免费额度为3；生成并发上限保持1。积分报价仅在开始后的弹层明确显示当次100与余额并要求确认，取消不创建；旧确认在报价变化后失效。处理同意用简短复选项及可展开说明保留，confirmProcessing/confirmPointsCharge wire与幂等/退款语义不变。原模拟面试和Global次数不得同步修改。

## 2026-10-18 失败定位与严格响应兼容

遵循 [失败诊断追加](failure-diagnostics.md)。原 wire 字段和 errorCode 类别不变；owner 的 errorMessage 可按固定无正文原因给出更明确中文提示，旧任务无原因时保持通用文案。固定诊断仅内部保存于既有 payload，和失败/原路释放同一事务；不得把内部字段、原响应或异常明细暴露出去。严格传输规范化不改变输出 schema、事实校验和计费合同，此次仅本地修复，不自动发布。

## 2026-10-18 失败诊断热修复生产授权

用户随后明确授权四文件CN Backend热修复上线，按[热修复生产规范](hotfix-production-release.md)重新冻结实际镜像/完整202路由schema/配置并执行七门禁、固定候选、受保护回退及独立验收。无DDL、环境、费用/次数、wire、Prompt或Web变化。另明确许可一次纯合成直接Provider定位及有依据修正后的同用例一次验证，不创建job/usage/账本，不碰钱包或用户资料，不自动重试/放松事实守卫；9.x本地记录保持历史准确性。

## 11.x 本地安全局部改写合同（优先于原单条错误整体失败语义）

用户已明确要求开发，11.x已按root实施GO完成本地开发/验收，未生产切换；精确算法、wire及自测边界见[安全局部改写合同](safe-edit-application.md)。全局JSON/schema/评分/evidence/语言/限长/最终稿仍整体严格；逐edit用原quote/事实/plain格式守卫独立拒绝，合格实质候选之间所有相交参与者全剔除，应用其余。canonical仅casefold+isalnum检测变化，不供事实匹配或正文改写。

新成功review可增editSummary：proposedCount/appliedCount/retainedCount与retainedReasonCounts{factCheck,sourceQuote,overlap,unchanged}，各严格整数0..24，applied>=1、proposed=applied+retained、四组和=retained；不接收模型自报，不存坏edit/replacement/位置/内部诊断。历史无字段正常，不回填。UI摘要只指AI初稿，未采用数不是未变区域数；非法meta不展示。

0applied且有非noop拒绝保留原序首个固定原因，全overlap为edit_spans_overlap；只有empty/allnoop/最终无实质变化用invalid_output及draft/no_effective_edits，固定基句“本次未生成可安全应用的有效修改，原简历已保留。”。失败无review/部分稿且原同事务原路退还一次，partial成功原一次settled，3次/100积分及claim/source/cancel/ledger保持。Web以code/固定基句/合法released后缀精确匹配回本地常量，退款独立呈现；Prompt v2仅新任务，原守卫不放宽。本轮本地开发/自测/预览，3例真实合成QA须候选隔离/私有配置/七门禁/单次marker，不生产切换/真实任务钱包资料/Git/Global/助手。

## 12.x 用户授权的安全局部改写生产合同

用户已明确授权上线；[生产追加规范](safe-edit-production-release.md)apply-ready待root独立strict/实际基线与实施GO。只发布已验收Backend3源/Web15patch，完整229→230/202schema/340Settings、305→315静态和原用户/金融/删除/事实规则保持。Web相对已验收候选唯一额外差异是offersteady-build.json的appVersion由.local改cn-resume-optimizer-safe-edits-20261018.1，其他14patch/JS不重编译或更名。正式release-patch另冻SHA。

原3免费/100积分与固定safe summary/errorMessage/no_effective合同不改；无DDL/有效环境/依赖/费用/额外真实模型/Git/Global/助手/Admin变化。实际基线、固定父镜像、完整七门禁/非目标签名/全字段Mounts、Backend→Web及受保护归属回退、实际禁网/NGINX权限读取和独立验收是生产硬门槛；忙碌等待，unknown/readfail/drift停止，不终止用户或清理活动。47已完成本地任务/75场景及QA历史保留，12.x不能预先标发布完成。

12.x模式窄修以[生产规范](safe-edit-production-release.md)第7节为准：实际旧Web模式SHA ae9835e7…绑定精确8原元数据755，其他原/15新patch/NGINX644、10目录755、316全部nginx可读；禁止glob/通用644或755及chmod旧文件。首轮dir1未切换，失败证据保持；新dir2只修probe并复用同Backend f6/Web2124eee8…固定候选，重新全部实际探针，root独立strict GO待记录，不追加模型/产品改动，12.2未完成。

最终dir3已按本合同上线并独立验收，52/52任务完成；前述dir1/dir2待执行描述为各阶段历史。实际固定双镜像、230/202/340/315/6非目标、精确模式/25隔离HTTP与两次19线上检查通过，观察窗口仅114.289/79.385秒；真实忙碌/回退未发生，无新增模型/费用/配置/DDL/Git，详见生产规范第9节。
