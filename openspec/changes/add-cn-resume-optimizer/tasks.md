## 1. 合同与实际基线

- [x] 1.1 明确国服每日1免费/其余100积分及本地范围，完成三能力和root批准的接口/金融合同
- [x] 1.2 绑定实际CN Backend/Web镜像、216个Backend输入、195条完整路径及既有优化保护基线
- [x] 1.3 读取apply上下文并记录root实施GO

## 2. 国服后端与金融

- [x] 2.1 CN功能域、路由/config/lifecycle及最小资料删除钩子，保留旧行为
- [x] 2.2 两表及账本约束迁移，保留未知旧kind/符号/不可变trigger并验证重复迁移
- [x] 2.3 真实会员/CN日次数、权威报价确认、同事务扣费创建及幂等重放
- [x] 2.4 同事务完成/失败/取消/源删/恢复终态与exactly-once退款，验证跨日/钱包并发
- [x] 2.5 独立有界worker、权限/删除/迟到屏障、草稿revision与真实资料另存；真实PG验证慢另存不持wallet锁阻塞旧钱包准入

## 3. 中文AI与导出

- [x] 3.1 独立中文Prompt/evals，事实改写正负/JD/注入/语言/数字/责任升级案例
- [x] 3.2 受控表格规范化和保守quote局部替换，原文件/Parser/快照不变
- [x] 3.3 真实DOCX/PDF中文模板、字体许可与混合/多页内容和渲染QA

## 4. 国服中文页面

- [x] 4.1 导航/资料入口/页面/client与输入/披露/评分/原文对照
- [x] 4.2 免费/100积分确认、余额不足/过期报价/跨日刷新/会员到期与钱包流水中文文案
- [x] 4.3 进度/失败/取消/删除、编辑冲突/下载/另存及错误恢复

## 5. 本地自测与交付

- [x] 5.1 本地隔离PG/API金融/并发/权限/删除/恢复自测及适用旧功能回归
- [x] 5.2 页面单测/typecheck/build、真实Chrome宽窄屏和API wire合同验证
- [x] 5.3 比对完整旧路由/schema/保护方法/Prompt/助手清单，冻结批准增量
- [x] 5.4 逐场景证据/命令/限制、OpenSpec strict与本地Markdown链接检查
- [x] 5.5 交付本地可测版本，确认线上/Global/助手/Admin/Git均未变

实施GO：2026-10-18 root已读取全部apply上下文并独立严格校验通过；Backend/Web代理已收到最终GO，仅本地实现和自测。

最终交付：2026-10-18完成19/19本地任务；142后端主套+1独立索引增量、11格式、313适用既有回归、456网页及32浏览器检查点证据保留。旧回归的1个Global专属跳过、1个旧源复现排除不算通过。仅本地开发，自测使用合成数据，线上/Global/助手/Admin/Git未修改。

## 6. 用户反馈回归修正

- [x] 6.1 修复合成预览误关模拟面试与刷新丢失配置，补同时导航/历史报告/真实关闭门禁回归和浏览器检查
- [x] 6.2 复核实际国服基线仍保留模拟面试实现，记录新增证据并重新严格校验

反馈修正：本地预览曾泛化关闭其他能力而隐藏模拟面试；已修复并增加4项真实组件导航/门禁及3项预览回归，整体Web463/463、typecheck/build通过，产物83文件中82项逐字一致，价格静态页由原构建流程重新生成。原32浏览器检查未覆盖两入口同时存在，缺口由本次IAB导航/报告/刷新检查补齐。现21/21任务、35场景；仅演示入口修复，无产品或线上改动。

- [x] 6.3 将5项无关公共静态输入与当前实际CN Web逐字对齐，新增可复现的保留回归并重新构建核对
- [x] 6.4 补齐基线修正证据、逐场景和当前线上只读复核记录，重新strict校验

当前线上只读复核后的基线修正：5项无关public输入已恢复实际线上字节，真实SHA失败5例→整体Web468/468通过，生产模式build/typecheck通过，对应5项dist相同；原10个产品运行时输入不变。原受保护manifest及早期结果保留，采用5项修正的current manifest，不覆盖历史证据。现23/23任务、36场景；未上线或提交Git。

## 7. 简洁页面与每日三次会员额度（用户最新修订）

- [x] 7.1 服务端统一国服3次免费上限，真实PG验证前三免费/第四积分、并发/跨日/释放/幂等，模拟面试和Global不变
- [x] 7.2 精简表单/历史/JD与处理披露，移除顶部费用大卡；积分按次弹层确认，保留全部结果操作
- [x] 7.3 更新合成预览与API wire，页面/导航/金融回归、类型与构建、宽窄屏实际浏览器验收
- [x] 7.4 冻结本轮增量和新证据、同步文档/逐场景/strict，交付本地供用户确认，不部署/Git

最新页面修订完成：会员3次/其余100积分且仅付费前确认；移除顶部费用卡、紧凑单列/独立历史/折叠JD和说明。实际PG147全套、Web480全套、typecheck/build及10个1440/390浏览器检查通过；9个真实本地API响应与Web副本一致。付费错误提示遮挡P2已修复，无剩余阻断。27/27任务、42场景。只交付本地供用户确认，未部署/重启/生产写入或Git。

## 8. 用户授权国服生产发布（2026-10-18 追加）

用户已明确要求将已验收的 20261018.2 上线国服供其测试；执行 [生产追加规范](production-release.md)，不改国际服/助手/Admin、不提交推送 Git。以下任务仅依据本轮实际证据完成，不用本地测试替代上线结果。

- [x] 8.1 重新冻结实际 CN Backend/Web 容器、固定父镜像、有效配置/标签、完整旧源/路由/schema/保护函数和全部静态/NGINX（仅新增新页面 allowlist 字面量）；确认仅批准增量及来源无漂移
- [x] 8.2 绑定控制器/输入/支持 SHA、候选/旧镜像回退与离线依赖，完成实际候选和完整旧行为/静态保留探针、公开文件/目录权限与真实隔离NGINX六路径200/SHA、控制器合成回归及 strict
- [x] 8.3 重复完整只读保护门禁，空闲时执行 additive 0054 迁移和仅 Backend→Web 固定切换；有活跃工作等待，不终止会话或绕过门禁，失败遵循归属及新用户保护回退
- [x] 8.4 独立 verify、公开/匿名鉴权检查、短时脱敏 ERROR/traceback/HTTP5xx 统计及原功能保护核对，按真实证据更新生产发布记录/逐场景/任务并通知用户测试

8.1 实际重新冻结完成：当前 CN Backend/Web 容器和固定镜像与本地绑定相符，216 旧 Backend 输入/195 旧完整路径与 schema、2337 未变旧函数/338 Settings 保留，全部294项旧静态与原 NGINX 完全相同。最终候选静态305项，只追加11项资源，4项入口HTML仅module URL及构建标识更新；NGINX仅新页面allowlist字面量。最终候选 main-edf518ca.js/ResumeOptimizerPage-756bc6ea.js，经独立逆向字节比对及24项实际组装Chrome检查。证据 `artifacts/cn-resume-optimizer-20261018-release/independent-source-overlay-audit.json`、`web/browser-assembled.json`；此处仍未声称实际镜像prepare或生产发布完成。

生产尝试记录：第一次prepare因真实Web build-only配置缺显式image失败，未切换。第二次已应用0054并切换双组件，公开验收HTTPError失败（原异常未保存路径/状态）；随后同固定候选隔离六路径403复现公开payload误设0600的权限缺陷，已在完整门禁/归属下回退固定旧镜像，原公开服务恢复，additive表保留。第三次需基于回退后真实新容器重新冻结，并在切换前取得固定候选实际隔离NGINX六路径200/SHA证据；8.2–8.4不能据旧本地或失败候选完成。

8.2 实际第三次候选完成：prepare-v3两固定镜像通过；完整实际Backend探针228源/202路径及真实合成DOCX/PDF/七类副作用0；nginx用户读取17新文件通过；固定Web候选真实隔离NGINX17GET全部200及预期SHA、0644，实例已删除。独立证据 `independent-actual-candidate-audit-v3.json`；失败候选/回退/旧audit结果保留。此记录仅完成8.2，8.3/8.4须后续实际发布/verify证据。

## 9. 2026-10-18 失败定位与严格响应兼容（本地修复）

用户反馈上线后的正常任务失败且无法定位；范围和验收见 [失败诊断追加](failure-diagnostics.md)。既往上线事实及 8.x 保持，本追加不自动发布/重跑原任务/真实模型调用/Git。以下完成情况只按新增本地证据更新。

- [x] 9.1 完成失败原因/包装边界/隐私/事务追加规范，root独立strict复核并记录本地实施GO
- [x] 9.2 Provider分项固定诊断、既有payload同事务持久化及owner安全中文消息，保持原类别/旧任务回退/退款和删除屏障
- [x] 9.3 严格兼容BOM/空白与整体单一json围栏；拒绝重复键/说明/多对象/截断，保留全部结构和事实守卫
- [x] 9.4 合成Provider/服务/真实隔离PG回归及AI evals，覆盖诊断、隐私、包装、事实正负及原子退款/竞态/旧任务
- [x] 9.5 独立审查、冻结修改与逐场景证据，运行strict/链接核对并准确交付本地结果和生产未更新限制

9.1 本地实施 GO：2026-10-18 root 独立 strict/apply-ready 复核通过，批准固定诊断、同事务保存及仅单一完整小写 json 围栏/BOM/空白兼容；31项既有交付事实保留，不推测旧失败细项。本次不调真实模型、不部署或改写原任务，验证全部使用合成数据。

9.2–9.5 本地验收：root合并六文件283通过，0失败/错误/跳过；独立最终四源码SHA一致、无P1/P2，8运行时组合通过。以已发布228输入核对225不变、3既有+1新增；9份合成HTTP结构与旧合同一致，旧wire未覆盖。两工作区strict及11份文档/22链接检查通过。证据见原仓库`artifacts/cn-resume-optimizer-failure-20261018/local-hotfix/verification.json`和`docs/releases/cn-resume-optimizer-local-20261018.3.md`。本次未调用真实模型、重放用户任务、生产切换或Git，旧失败的精确原因仍未知。

## 10. 2026-10-18 失败诊断热修复生产授权

用户已明确要求优化完成后部署上线，并许可一次纯合成真实Provider定位；遵循[热修复生产规范](hotfix-production-release.md)。9.x本地历史及其283通过证据保持，不把其当作已上线结果。本轮只允许CN Backend四文件增量，不改DDL/环境/费用/Prompt/Web/Global/助手/Admin或Git。

- [x] 10.1 root复核追加规范/strict并GO，重新冻结实际Backend995ae331…父镜像、228源/202完整路径schema/有效配置和全部非目标，确认只四文件增量
- [x] 10.2 绑定控制器/七门禁/输入SHA与固定候选/回退，完成控制器合成回归及实际禁网只读无生命周期229源/原路由配置/诊断事实探针
- [x] 10.3 完整门禁后执行最多1次纯合成直接Provider定位；必要时仅按固定原因有据修正/补eval与回归重冻结，再同用例1次验证，不建job/扣费/读取真实资料或盲重试
- [x] 10.4 完整重复七门禁空闲时仅Backend固定切换；无DDL/配置或非目标重建，失败遵从归属/新活动保护的固定回退
- [x] 10.5 独立verify完整源/路由schema/配置/原功能和非目标，记录真实合成结果与短时脱敏错误统计，更新发布/逐场景/strict并通知用户测试

10.1 实施GO：用户最新明确授权已记录，root独立strict与apply-ready复核通过；只读actual-baseline确认Backend4667f8b8…/995ae331…、Web029e84e0…/20d6a03a…、228源与发布映射相同、202路径/340有效Settings/305静态、七非目标身份与摘要。首次七门禁可用且保护活动全0。批准四文件Backend-only候选、独立实际探针、七门禁后一次合成直接Provider；不操作真实任务/钱包/资料，不放宽守卫，不改其它组件或Git。之后切换和验证仍以最新完整门禁为准。证据目录`artifacts/cn-resume-optimizer-hotfix-20261018-release/`。

10.2 实际候选准备通过：新Backend固定镜像6f2a53f5…直接派生995ae331…，Config/父层保持；实际禁网只读229源/202完整路径同原schema2f030c…、合成DOCX/PDF及七类副作用0。控制器45回归、独立122保护检查和payload全SHA审查通过；线上仍原4667f8b8…/995ae331…健康重启0。证据`actual-candidate-evidence.json`、`production-prepare.json`。尚未真实Provider或生产切换。

首次热修复preflight停止记录：尝试1prepare/独立实际候选验收完成后，preflight报non_target_identity_or_configuration_changed；只读聚合定位PG Mounts摘要不同，其他身份/Config/HostConfig/完整网络保持。尚未真实Provider/切换。完整原值排列验证仍待root证实，不据此声称PG实际改挂载。若证实纯排列，仅按[追加窄规范](hotfix-production-release.md)全字段/保留重复规范化，使用新dir2重新freeze/回归/独立审查/实际prepare；10.2上述成功只对应尝试1，不代表修正后的新候选已完成。10.3–10.5保持未执行。

挂载顺序核对后续事实：root只读证明全7非目标完整Mounts多重集保持，PG两条的不同排列可精确复现d6d61…与229772…，确认为inspect顺序误报而非实际挂载修改。root批准全字段/重复保留canonicalMounts和新controller-v2/dir2；v3新基线00e57147…只有atMs和PG稳定mountsSha变化，其他完整字段保持。10.2现重新待执行，直到新工具/候选回归、独立审查及实际prepare通过；上述10.2尝试1成功和随后preflight停止均保留，不拿旧证据代替新修正结果。线上和真实Provider仍无切换/调用。

10.2 新dir2重新完成：controller-v2 e5ad4d31…/input e6c6bc42…/v3基线00e57147…全部绑定，60控制器回归及独立挂载字段/计数检查通过；实际prepare-v2仍为同6f2a53f5…候选（四业务源未变），229源/202路径/原schema/合成DOCXPDF及七副作用0，Config/父层保持。actual-candidate-review-v2.json独立核对通过；production-preflight-v2.json真实通过，无生产切换。任务10.2据新证据恢复完成；v1 preflight停止与排序证明完整保留。后续一次Provider和切换结果仍待其独立证据，未提前完成10.3–10.5。

10.3 真实纯合成Provider验证通过：dir2固定candidate6f2a…在再次实际禁网probe/完整七门禁后仅请求1次，19335ms，4评分维度/5建议/6待补事实/806字符稿，全部解析/事实守卫通过；receipt绑定candidate/4源码/脚本/合同/合成case/input e6c6…，不创建job/usage/钱包/面试或读取真实资料。无需额外模型请求或事实/Prompt修正；不能等同原用户失败任务已定位。证据production-provider-check-v2.json。

10.4–10.5 实际发布与验收完成：北京时间2026-10-18 05:07:33.546仅Backend切换到b955c33e…/6f2a53f5…，05:08:35.669独立verify通过，冻结controller e5ad4d31…/input e6c6bc42…相符。最后七门禁exit0/保护0、容量样本23.508秒；229源/202完整schema/340Settings/原配置与7非目标/305静态保持。7公开200及原HTML/build SHA、2匿名401/private,no-store通过；Backendhealthy/重启0。短时实际覆盖Backend107.969秒/Web87.266秒，各ERROR/traceback/HTTP5xx0、固定诊断空/unknown0、未截断。IP未变，无proxy reload/非目标重建/生产回退，无DDL/配置/费用/Prompt/Git或Global/助手变更。一次19335ms纯合成Provider已独立核对，不建真实任务/钱包/资料，不认定旧用户历史根因；dir1停止及顺序误报证据保留。final-release-audit.json通过，无剩余阻断，41/41任务完成，交由root最终确认并通知用户测试。

## 11. 2026-10-18 安全局部改写与失败说明（本地开发）

用户已明确要求开发，当前[合同](safe-edit-application.md)已获root独立strict实施GO。41项历史完成保留，以下状态仅按已取得证据勾选。本轮本地开发/自测/预览，不生产切换/Git/Global/助手/Admin或费用DDL环境变更。

- [x] 11.1 评审新安全选择/零有效失败/计数/Prompt/UI合同，核对实际6f2a/20d6基线并记录root明确实施GO
- [x] 11.2 Provider全局严格+逐edit原守卫/全部重叠剔除/实质变化与首因，服务端editSummary及no_effective_edits诊断、CN Prompt v2和AI eval
- [x] 11.3 Web固定code/消息白名单及权威退款、合法AI初稿计数/旧meta兼容/私密回退，不虚称未变区域，保留原页面与操作
- [x] 11.4 本地真实PG/API partial结算及零有效退款/事务故障/重放/claim-source-cancel竞态，合成Provider/AIeval和适用旧功能/wire回归
- [x] 11.5 Web组件/安全摘要/历史轮询、typecheck/build和实际本地编译/静态组装Chrome，保留原导航/305静态/CSS/NGINX并交付预览
- [x] 11.6 候选隔离只读探针和完整七门禁后最多3长技术纯合成例各一次直接Provider QA，绑定marker/安全摘要/独立审查/strict；只本地验收，不生产切换或真实业务写入

11.1 GO前的只读基线记录（后续GO见下一段）：root取得229完整源与工作区逐字一致、202 OpenAPI/schema/340Settings/305静态及NGINX匹配，Backend b955…/6f2a…、Web029e…/20d6…；current-baseline.json SHA08a10e80…位于artifacts/cn-resume-optimizer-safe-edits-20261018/。当时实施GO尚待root，未提前勾选；后续已按下段明确GO实施。root负责新独立PG/API金融测试文件与wire，Provider/Web代理在GO后按各自范围实现。

11.1 root实施GO：2026-10-18独立读取全部apply上下文及safe-edit合同，严格校验通过、state ready（41历史完成/6新任务）。实际229输入/202完整schema/340Settings/305静态基线已核对。批准按11.x合同本地Provider/Web/PG/API及预览开发，最多三例隔离合成QA须另外逐例七门禁/marker和冻结验收；不执行生产切换/Git/Global/助手/Admin，原收费/事实/状态守卫保持。

11.2–11.4阶段记录（当时11.5/11.6待验收，最终结果见后文）：Provider/v2及42新AI eval、Web固定消息/计数和真实PG/API已实现；根合并391通过，随后仅追加的2条AI eval使最终新Provider88通过，去重393案例，22项PG/API覆盖partial settled/零有效原路退款/故障回滚/迟到屏障/历史v1。Web60文件568通过、typecheck和production build通过；actual静态组装315项保留305旧路径（4HTML仅URL和build标识5项允许覆盖），CSS/NGINX不变。11.5实际compiled浏览器与11.6隔离真实QA仍待验收，不能据此声称上线。

11.6首轮QA工具停止历史（后续dir2结果见最终验收段）：dir1的actual-prepare已通过candidate912137e9…/230源/202路由schema/340Settings及七副作用0；case1完整七门禁通过后于Docker/runc init嵌套只读挂载阶段失败，容器进程未启动、Provider请求0、后例未开始，旧marker保持consumed。按合同第9节仅修QA staging/单目录挂载，另用dir2/controller/plan/tag和实际Linux Docker禁网演练重冻；root重审前不调模型。本轮实际模型验证仍未通过、11.6不勾选，不改产品/上线范围或总实际请求<=3预算。安全证据first-attempt-safe-diagnosis.json和actual-case1.json保留。

11.5已完成：追加真实PG/FastAPI wire四项后Web61文件572/572及类型检查通过；315候选静态逐字服务、原CSP，IAB/Chrome 13个实际操作观察点通过，包含partial新建轮询/初稿摘要/编辑保存/WordPDF入口/原Mock列表报告、无有效修改历史和轮询失败原因/退款/主动重试、Chrome已知事实原因和100积分退款。1003个loopback HTTP断言、SHA/100%静态核对通过；仅合成预览，不调用模型、不宣称390px已重做。预览5178和实际compiled5181保留，browser-verification.json有准确边界。

11.6最终实际验收完成：新dir2候选f6dbe8fd…禁网完整230源/202schema/340Settings/真实DOCXPDF/七副作用0，Linux单目录只读挂载演练通过，完整七门禁/marker后3合成例各1请求，总3次；19.693s/21.130s/22.835s，采用5/7/5项，第二例2项unchanged未采用。最终actual-verify-v2 complete true，源/配置/非目标和原静态保持，生产切换/业务写入0。dir1的runc预启动故障已明确0请求且旧marker不改，26工具回归/独立审核后新目录恢复原预算。47/47任务本地完成，真实QA不是生产上线或用户原任务重放；证据及限制详见local-20261018.4文档。

## 12. 2026-10-18 安全局部改写生产发布

用户已明确授权上线；47/47本地及历史任务保留，下列5项已按真实发布证据完成。遵循[生产追加规范](safe-edit-production-release.md)，用户授权、root独立strict/实际基线GO、实际候选和重复七门禁均已取得，无额外模型。

- [x] 12.1 root独立复核12.x范围/strict并GO，重新冻结实际CN Backend/Web完整源/202schema/340Settings/305静态/有效配置/归属和全部非目标，绑定本地final-verification
- [x] 12.2 冻结Backend3源/Web15正式patch及唯一build标识差异、控制器/完整七门禁/固定候选回退SHA，完成工具合成回归、实际候选禁网230输入/原功能与Web精确8原元数据755、其余原/新/NGINX644、10目录755及316可读HTTP/SHA隔离验收
- [x] 12.3 完整重复七门禁空闲时按固定Backend→Web切换，忙碌等待/unknown-readfail-drift停止；部分发布核归属跳过已完成步，失败按同门禁Web→Backend固定回退保护用户
- [x] 12.4 独立verify两目标镜像/归属/完整源路由配置静态和非目标、7公共GET及匿名401/private,no-store与已验收safe-edit行为，禁止真实模型/用户任务费用测试
- [x] 12.5 完成短时脱敏错误/固定诊断统计并注明覆盖秒数，保留全部历史和真实部分状态，更新发布记录/场景/strict及链接后通知用户正常账号测试

12.1只读基线部分已取得：root新生产冻结证据artifacts/cn-resume-optimizer-safe-edits-20261018-release/current-baseline.json，SHA5a670a02c4484dde6d01056ed1908aa3edb0680ee80df52db412add3043e748a；除atMs外与已验收QA基线每个完整字段相同，实际229源/202schema/340Settings/305静态/NGINX/全部非目标、Backend healthy/重启0保持。此事实只完成12.1的基线部分，root独立strict实施GO尚待记录，12.1暂不勾选，不代表候选/发布完成。

12.1 root生产实施GO：2026-10-18用户明确授权部署，root独立读取全部apply context及12.x生产规范/待发布记录，strict通过且ready（47历史完成/5新任务）。重新实际freeze5a670a02…除atMs外完整保持，绑定final-verification dc869f66…。批准仅CN Backend已验QA固定f6dbe8fd…三源与Web15正式patch（仅build标识额外.local→.1）生产工具/候选准备、实际禁网/NGINX验收及重复七门禁后Backend→Web切换。任何busy等待、unknown/readfail/drift停止，受保护归属回退；无DDL/环境/额外模型/真实测试任务/Git/Global/助手/Admin。12.2–12.5须后续实际证据，不据GO提前完成。

12.2首轮停止：dir1实际Web2124eee8…内容/NGINX/Config/旧层部分已核，模式probe阻挡；未切换/未模型。316全部可读，旧20d6模式基线SHA ae9835e7…证明精确8原元数据755/其余644、10目录755。12.1原GO保持，12.2仍pending，按生产规范第7节仅修probe，新dir2/controller/input/token/tag复用同Backend/Web候选并重验全部实际探针，新增严格模式反例；保留dir1，不chmod/改产品/追加模型，root独立strict窄修GO待记录。

12.2 dir2窄修root实施GO：root独立核actual-baseline-public-modes SHA ae9835e7…与候选316逐项诊断，精确8旧AppleDouble0755完全相同、其余0644/10目录0755/全可读；独立读取第7节与能力场景，两根strict通过。批准仅新controller-v2/payload-v2/dir2固定Backendf6和Web2124候选复用、精确原模式probe和最小回归；保留dir1所有输入/失败，不build/chmod/改产品/额外模型，所有七门禁及归属保护保持。实际prepare/切换尚未完成，12.2继续pending。

12.2 dir2停止历史：原306/候选316模式与Backend230/202副作用0均通过；隔离网络publish映射为空，HTTP前TypeError。按生产规范第8节新dir3仅修隔离地址读取，实际私有IP诊断25项全通过不代替prepare；原两目录全保留，12.2继续pending。root strict与窄修GO随后记录。

12.2 dir3 root implementation GO: root independently reviewed section8 and the actual diagnostic 690ad7c6 (25 real HTTP/hash checks and owned cleanup passed), both roots strict passed. Approve only new dir3 isolation transport using exact owned internal-network private IPv4, no published port; preserve both fixed images, all gates/recovery, mode rules and prior failures. New prepare and production cutover remain pending.

12.2 actual v3 completed: controller c6dce7b3/input9aa65c2d, 115 tool regressions and independent reviews, fixed Backendf6/Web2124 reused; actual prepare/evidence verifies230/202/340/315, real DOCXPDF and seven side-effects0, exact306/316 modes and 25 isolated HTTP/hash requests with owned cleanup. Both prior stopped attempts preserved; preflight passed complete seven gates, no production switch implied by this task. See release evidence and independent-audit/actual-candidate-v3-review.json and web-actual-candidate-review-v3.json.

12.3 actual v3 deployed: fresh preflight complete seven gates passed; the fixed controller repeats complete gates inside the lock before Backend and Web recreation. Both now new (Backend50bcb76f/f6dbe, Web88ae70c9/2124), actual-deploy-v3.json deployed true, 19 public checks passed. No busy/partial production recovery occurred; those negative cases remain covered by the frozen115 synthetic tool tests. Existing configuration and six non-targets/shared tag remain protected. Independent verify and short observation pending.
