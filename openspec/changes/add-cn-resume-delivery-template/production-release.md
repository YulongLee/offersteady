# 国服商务简历 PDF 模板生产追加规范（6.x）

状态：用户已明确授权国服部署，6.1–6.4已按本规范完成实际候选、受保护单Backend切换、独立verify及180秒短观察，最终独立上线审查也已通过；6.5的双根strict/链接与发布记录收尾已通过。实际结果见[验收](verification.md)及[生产记录](../../../docs/releases/cn-resume-delivery-template-20261019.1.md)。1–5.x的11/11本地任务、769最终样式、D1–13及全部失败记录保持历史；以下合同不因工具修复或成功切换而放宽。

## 1. 授权与最小发布范围

国服简历优化主体、AI安全局部改写、计费和Web下载入口已经上线。本次只使原PDF下载使用已验收商务模板；不重发AI/计费/失败说明等无关增量。默认目标严格限定 **CN Backend一个组件**：新增CN专用renderer并替换CN service默认PDF分发，DOCX仍调用原共享helper，injected exporter及前后两次owner/source/completed/revision/factsConfirmed守卫保持。

现有线上Web即可请求相同PDF接口，因此本规范不包含Web发布；本地Page简短说明不属于模板生效前提。Web全部静态/NGINX作为非目标冻结保留，不将83文件本地标准build替换线上静态全集。若root随后判定Web说明必需，必须先补充实际Web完整基线、精确增量/全量保留与独立验收规范并重新GO，不能在单组件发布中临时附带重建Web。

本次不运行额外迁移/DDL/修复数据、修改环境/依赖/字体/模型预算/费用、调用真实模型、读取真实用户简历、创建生产测试任务/资料/面试/usage/钱包或账本、重放用户任务或压测；不提交推送Git、不更新Global/助手/Admin等组件。会员每日3次/其余100积分和模拟面试等政策保持。原简历/已保存稿与用户已产生数据/费用不得因发布或回退改变。

## 2. 已验收输入与本轮新鲜生产绑定

本地固定来源为[商务版本地记录](../../../docs/releases/cn-resume-delivery-template-local-20261018.2.md)、[上一轮本地记录](../../../docs/releases/cn-resume-delivery-template-local-20261018.1.md)及原仓库 `artifacts/cn-resume-delivery-template-business-20261018/`。170项后端、10份14彩页/2灰度逐页视觉、6项真实本机HTTP及独立源/抬头边界是已完成本地事实，不能代替实际生产候选或上线验收。旧Web586/83只为未改源历史，不冒领本轮重新build/browser执行。

Backend产品源allowlist只有两项：

| 相对路径 | 已验收SHA-256 |
| --- | --- |
| apps/backend/app/services/cn_resume_optimizer_export.py | 76925432e1c8c7ac7801e8cc4978fba67641af65f8c1a7e748bf0593fc0f523d |
| apps/backend/app/services/cn_resume_optimizer_service.py | 4caa2319066a654320f07527dac5243d0431b7382a57a8e1e1d4d0dbba0e2d66 |

renderer只能为已验收字节；service须同时证明相对实际旧service的整模块AST仅默认PDF lazy分发变化，注入/Word/原两次get/错误/收费语义保持。不得整文件取主仓混合源码覆盖、夹带测试/本机桥接/样例或改Prompt/Provider/repository/config/路由/模型。

root必须重新只读冻结：实际Backend容器/不可变image、完整输入清单、完整OpenAPI routes/schema、Settings字段及有效配置摘要、完整Config/HostConfig/全部字段Mounts/网络/Compose归属/重启和启动身份；实际Web全静态/NGINX/模式/公开HTML与build摘要；全部非目标容器/共享tag。`current`、健康版本字符串、旧目录或共享标签不能代表组件现状。Mounts只规范化最外层排列，字段/值/未知字段/重复和嵌套数组全部保留。

root已新鲜只读取得 `artifacts/cn-resume-delivery-template-20261018-release/current-baseline.json`，SHA-256 `007c9fddb42158eb214be28ceac2e2922a89552d38ad67a44c9d0c606d4c63b5`；本规范只绑定实际读取事实，不表示候选/上线已完成：

| 实际项目 | 冻结值 |
| --- | --- |
| Backend容器 | `50bcb76f5b05603bcd3071bbd622a95a6a91009c5837fbc9f88cb67c1b560dd3` |
| Backend实际父/回退image | `sha256:f6dbe8fd498f1f965bf8ba611d666e7ea49475ac1a7bf01b547ed79e8c6bbfaa` |
| Web非目标容器 | `88ae70c9fd1bdf39dd5f7b2f15b54266ca058e23b843ced2d24e22ba15eaaf38` |
| Web实际image | `sha256:2124eee829453776d6191b669c29a28c06f83a011bb6b8461432fefd1393463d` |
| 完整原输入/完整schema/Settings/Web静态 | `230 / 202 paths / 340 fields / 315` |
| 完整OpenAPI/schema摘要 | `71caf5370ba9071756b5b2f5758c33059a773e466ece331633d696a3ffc27f9d` |
| Settings有效摘要 | `8da0d5c924f42fafe26d5f3e5816837a47beb2d026ca7514e92ba36774c79efe` |
| 原Web NGINX摘要 | `b461e58972c10f64398fac815556feec8306b441a82c8252ba48194b36d3bb3b` |

Backend healthy/running、restart0；Web running/restart0，6个其他组件原归属/配置/运行保持。基线JSON将Web列在components、另有6个nonTargets；本次Backend-only计划必须将原Web完整签名并入 **第7个非目标**，不能因旧双组件数据结构漏保护Web。全部后台worker仍是非目标，禁止重建或改策略。

上述发布前实际基线尚无新renderer；最终delta精确为769新renderer与4caa旧service替换，229旧输入逐字保持，230→231。service整模块AST只允许默认PDF分发变化，其他旧源/完整202schema/340Settings/315静态与有效配置保持。任何后续真实漂移均停止；再次执行发现已部署须核对实际归属/结果，不重复重启。6.1的root独立strict与实施GO已记录于root-implementation-go.json，后续实际候选独立审查与切换GO分别留证。

生产服务器目录拟冻结 `/opt/offersteady/releases/20261019-cn-resume-template-1`；本地证据沿用 `artifacts/cn-resume-delivery-template-20261018-release/`，其中20261018是任务产物名称，不代表实际生产日期。

私有环境/Compose原文/原始日志只留服务器，发布根0700、私有文件0600；本地只存脱敏摘要/哈希/聚合。候选父镜像、原RootFS层前缀与Image Config保持，不安装包/下载字体、移动共享tag或改既有启动/端口/挂载/网络/环境策略。

## 3. 专属控制器与实际禁网候选

复用[先前正式发布规范](../add-cn-resume-optimizer/safe-edit-production-release.md)与已审单Backend控制器的固定digest、完整七门禁/归属/只改image overlay及受保护恢复原语；本次独立发布根/输入/支持文件/控制器SHA/计划/候选与回退专属tag，不能复用旧prepared/progress或把QA工具当发布器。controller/plan/每项支持文件必须双向绑定，精确拒绝额外/缺失/符号链接payload。

prepare只能冻结原镜像回退并从实际父digest派生两源候选，不切业务。候选实际输入必须逐项匹配计划，全量schema/Settings/effective digest与原保持、原字体/shared helper/Prompt/金融/mock/鉴权性能补丁等均原SHA；候选只读、network=none、禁止提权/限资源，不进入业务lifespan、不连接数据库/模型/对象存储、不写业务文件或启线程/子进程。既有副作用探针七类计数均0，字体只读可用不算写入。

实际固定候选必须真实导出纯合成 **CN商务PDF和原DOCX**，证明service默认PDF路径使用新renderer、Word原调用/同稿部件保持、原前后授权/修订屏障未动。检查真实文件签名/MIME/A4、内嵌真实中文/中英文文字、完整原序/数字日期/联系/尾标记、字号/正文不缩、band/无title/超高回退、长label/标点/长URL/长段自然分页与安全固定错误。检查不得仅import或伪文件头。若实际镜像不含PDF解析测试库，可将纯合成输出交独立隔离解析器/本地解析，不向生产镜像安装新依赖，不处理用户稿。

候选冷启动/实际生产运行由后续健康验收独立证明，禁网探针不得为此开启真实业务lifespan。controller回归应覆盖实际父image选择（不继承旧默认参数image）、双门禁、额外TCP/netns前后身份/非零defer/读取未知停止、仅恢复stoppedProcessProof完整正反条件、忙碌/unknown/readfail、exact allowlist、全量配置、归属/意图重入、已部署不重启、冷启动失败/受保护恢复及非目标保持；通过后root与独立审查绑定实际候选digest。

## 4. 原完整七门禁与单组件切换

以下只读门禁代码、字段/阈值/新鲜度由本次实际旧Backend父digest执行并逐SHA绑定：`legacy-gates/idle_gate.py`、`legacy-gates/check-idle.py`、`legacy-gates/readiness-idle.py`、`extra_idle_gate.py`、`active_work_gate.py`、`resume_optimizer_idle_gate.py`、`financial_idle_gate.py`。完整保护live/recent preparing/页面与音轨/桌面令牌发布端、文字/截图/采集工作、mock阶段/生成租约、资料处理/删除/对账、有效未付订单/近期支付回调及CN optimizer未完成jobs/usage；金融门禁只作这些既有只读保护，不新增对后台worker的调度/停止/重建；不能只看面试计数或健康接口。

preflight与真正切换前必须在同一发布排他锁、重新核对完整源/配置/容器归属后分别执行完整七门禁，至少两次新鲜有效全零；实际切换前再复核不得复用旧样本。仅真实保护活动非零且其余数据合法的`protected_user_work_cutover_deferred`允许保持原服务等待。unknown/readfail/缺失字段/非法值/扫描超限/样本过期/进程失败或source/config/controller/归属漂移必须停止自动操作并报告；不能当忙碌静默重试，不能结束用户、清理jobs/租约、改TTL或放宽门禁。

### 4.1 额外Backend TCP在途保守检查（不改原七门禁）

为减少同步PDF/Word导出仍在途时切换的风险，发布器在最终preflight、真正切换前和恢复临近，完成原七门禁后额外只读聚合**实际目标Backend网络命名空间**内本地TCP8000的ESTABLISHED连接（IPv4/IPv6），不关闭连接、不调用业务API、不输出地址/端口对端或原始socket行、不修改服务/API/配置/TTL或重启策略。它不是七门禁替代，也不增加金融worker语义。

普通检查只能针对本次核定/精确归属且Running=true、有效Pid>0、非Restarting/Dead/Paused的目标。读取前后分别inspect，要求同ID/image/StartedAt/Pid/重启状态及完整归属/Config/HostConfig/Mounts/网络保持；固定读取脚本在容器内核对执行进程与目标进程网络命名空间一致，并将实际netns标识与前后身份绑定。解析/IPv4或IPv6读取/身份或netns校验失败属于unknown，停止自动操作，不可当作0。输出只保留聚合数和身份/校验安全摘要，不含socket地址。

真实有效TCP计数非零时，按protected_user_work_cutover_deferred保持现有服务等待；只有有效实际读数0才能正常preflight/部署。最终切换/恢复临近重新读取，不复用preflight旧TCP样本，不在读数0后额外调用会制造Backend连接的验收请求再冒称同一次在途保护。

新鲜基线 `gracefulStop` 显示Docker StopTimeout为null，且无explicit `--timeout-graceful-shutdown`；沿用现有graceful机制，不新增参数或修改配置。原七门禁+额外TCP读数只是降低风险的瞬时非原子保护；0 sockets不证明零应用工作/zeroinflight，不承诺绝对零竞态或零影响。

### 4.2 仅恢复可用的已退出进程证明

唯一窄例外仅限恢复路径中**本次精确归属candidate**的已知cold-start exited失败：前后两次inspect均严格 `Running=false / Pid=0 / Status=exited / Restarting=false / Dead=false / Paused=false`，同一ID/image/StartedAt及其余完整归属/Config保持不变，才可用无进程停态证明替代TCP读取。结果须明确 `stoppedProcessProof`，表示没有可执行TCP读取的进程，**不得伪装为读到了0 sockets**。原完整七门禁仍须全部有效空闲，然后才恢复本次冻结旧digest；不关连接、不改restart策略。

此证明不能用于正常preflight或部署，二者必须Running并实际读取TCP。Running时exec读取失败、未知状态、Restarting/Dead/Paused、Pid/身份/归属变化，或不能完成前后双确认，均必须停止，绝不能通过catch泛化套用例外当0。恢复中的实际运行目标仍须按4.1真实TCP读数；一般命令失败也不能因此直接被分类为已知可恢复cold-start。

全部通过后，仅用本次专属固定candidate digest的image-only Compose overlay切换CN Backend，保持完整有效配置与全部非目标；禁止额外build/pull/migrate/force-recreate其他组件或更新Web build标识。记录切换意图、结果与新容器归属，验证实际image/running/healthy/冷启动/restart0；意外中断后必须按真实state核归属，不重复切换已完成目标。

Backend IP不变则不动代理。只有IP实际变化且现有Web/Admin必须刷新DNS时，允许沿用既有机制先对原容器`nginx -t`再reload；不改任何配置字节、镜像/容器/启动身份，不构成Web/Admin发布。语法失败/归属漂移停止并报告。门禁是瞬时快照，不能承诺绝对零竞态或用户影响。

## 5. 固定旧digest恢复与独立验收

只对本次仍有精确归属的Backend、已知且可恢复的健康/公共验收失败，才可在完整相同七门禁再次有效空闲，且（临近TCP实际有效0，或满足4.2严格stoppedProcessProof）时恢复本轮冻结的原digest/原有效配置。普通命令失败、unknown/readfail/漂移/归属改变必须先停止，不得泛化触发自动回退；活动非零时保持当前安全状态等待/报告，不绕过门禁。恢复只切镜像，保留全部原表/任务/已保存稿/原文件/真实账本和新结果，不删数据、不撤销消费或重放用户任务。恢复失败则停止自动操作并报告所需处置。

独立verify必须核对实际新container/image/本次归属、healthy/running/冷启动/restart0、完整231源（或root实际冻结数）、完整原schema/Settings/effective config、全部Web静态/NGINX/非目标/共享tag保持。7类公共GET至少覆盖健康、登录、普通/模拟/笔试入口、简历优化及build，状态200且原HTML/build摘要保持；匿名optimizer能力与导出仍401/private,no-store。不能代用户登录、创建真实测试job或导出真实用户稿；实际模板效果由固定候选纯合成文件及已验收本地证据证明，再由用户用正常账号自行测试。

短时观察仅统计新目标实际启动后的脱敏ERROR/traceback/HTTP5xx与固定诊断计数，写明覆盖秒数/是否截断，不导出原日志/用户标识/简历/会话。异常按真实归属及相同活动保护处理，不把短时结果冒称长期P95、全部真实用户简历或所有打印/ATS兼容。

完成后更新6.1–6.5、本轮D14–20及实际生产记录，保留11/11本地/旧失败与旧PDF证据，通知用户通过原简历优化页面重新下载测试。当前实际候选/切换/verify、180秒观察和最终独立上线审查已通过，未发生恢复；6.1–6.5及双根strict/链接收尾均已通过，全部状态按实际证据填写。
