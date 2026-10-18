# 国服安全局部改写 20261018.1 生产追加规范（12.x）

状态：2026-10-18国服dir3实际发布、独立verify/全量运行快照和短时脱敏观察完成，12.1–12.5全部完成，合计52任务/81场景。原计划及dir1/dir2的prepare停止事实保留，实际最终结果见第9节；本地47任务/75场景及三例模型历史不回写。

## 1. 授权范围与固定验收来源

只上线已验收的CN安全局部改写、无有效修改失败退款、v2 Prompt、固定安全错误说明和AI初稿计数UI。[本地合同](safe-edit-application.md)的产品/金融/事实边界保持：会员每日3次免费、其他100积分及显式付费确认、原claim/revision/source/cancel/账本屏障不变。原普通/模拟/笔试、收音、资料、支付、钱包、已发布鉴权/状态/预取及Global政策保持。

本地验收固定来源为原仓库`artifacts/cn-resume-optimizer-safe-edits-20261018/final-verification.json`，SHA-256 `dc869f662e1d64639dd3e549c4d1113fec632fe0643743260d86499918ae1cd9`：47/47任务、75场景、393不同Backend案例（含22项真实隔离PG/API）、42新AI eval、572Web/typecheck/production build、13实际IAB/Chrome检查、1003合成HTTP检查、26工具回归及三例真实纯合成Provider各1请求通过。三例分别采用5/7/5项，第二例仅2项无实质变化未采用；事实违规partial由本地负例/真实PG/API证明。不得重放原用户任务、读用户正文或据此声称所有简历/长期质量已验证。

本次不DDL/迁移、不新增或修改运行环境/依赖/模型预算/收费、不额外调用真实模型、不创建生产测试job/usage/账本/资料/面试、不压测；不更新Global/助手/Admin或Git。历史0054已存在，仅只读确认兼容，不重跑迁移、不改旧行/约束/trigger，不清理受保护活动。三例模型QA及dir1挂载预启动失败0请求、consumed marker/dir2修正和全部旧发布失败/回退证据保持。

## 2. 重新冻结实际生产组件

root先只读重新核对Backend/Web实际运行容器、不可变镜像、完整源/路由/schema/Settings/有效私有配置/Compose归属/挂载/网络、全部旧静态和NGINX；预期Backend `b955c33e…` / `sha256:6f2a53f55ac6343c983234fedde62bd46432a1087c75705425c267971bf3d581`，Web `029e84e0…` / `sha256:20d6a03a6acdc923f02cc786af2cdd862599b4e65ef1d2dbc9fd77be7c163610`，这些只是待确认预期。实际仍应为229个Backend输入/202条完整OpenAPI路径及schema/340个Settings、305旧Web路径；任何真实漂移均停止自动切换并报告，不从`current`、旧目录、健康版本字符串或共享标签推定现状。

全部非目标（Web本轮是目标）身份/启动时间/固定镜像、完整Config/HostConfig/挂载/网络/重启计数和共享标签绑定。沿用已审全字段`canonicalMounts`：只规范化Mounts最外层排列，全部条目/现有及未知字段/值/重复数量保留；嵌套数组和完整HostConfig保持，真实差异仍拒绝。私有配置只留服务器，不导出环境、密钥、挂载路径或原始用户日志。

## 3. 仅三源与十五公开文件的增量

Backend固定从重新确认的实际6f2a父镜像派生，只覆盖以下两旧源并增加v2 Prompt；其余227旧输入及原v1 Prompt/全部schema/迁移/运行生命周期/服务和仓库保持，229→230输入。发布前重新核对完整SHA，不用QA镜像标签代替实际生产候选来源：

| 相对路径 | SHA-256 |
| --- | --- |
| apps/backend/app/services/cn_resume_optimizer_provider.py | 92df5298dccbc13473a11ee51a5042b4e8629bf14a157371cf75e6ee1553609b |
| apps/backend/app/services/cn_resume_optimizer_diagnostics.py | 0748bc7a8cdc05f31ba6184e22196da668e5f839a45137ee62ac2fb792f465ea |
| ai/prompts/resume-optimizer/review.zh-CN.v2.md | 58cfa54bca5556aaa7640b3bd9da5761369c4afbddd2c96ef67c0c26dee6cd80 |

Web固定从实际20d6父镜像派生，只追加/受控覆盖已验收15项patch，305原路径全部保留、总315。10个新JS（新页面`ResumeOptimizerPage-d573f53f.js`和9个仅传递URL的模块，其中入口为`main-09170906.js`）沿用本地已验收字节与hash，不重编译；仅Page有已审安全提示/计数语义变化，其余9个新模块反向还原URL后逐字等于各自原模块。原所有旧hash资产不删除/覆盖，CSS/NGINX、SEO/价格/媒体/错误页和公开正文保持。

允许覆盖的5个既有公开路径仅为`index.html`、`guide.html`、`terms.html`、`privacy.html`的module URL，以及`offersteady-build.json`。相对已验收315本地候选，本次唯一额外差异是build元数据`appVersion`由`cn-resume-optimizer-safe-edits-20261018.local`改为正式`cn-resume-optimizer-safe-edits-20261018.1`，`appEnv=production`与`apiBaseUrl=/`保持；其余14patch必须逐字相同，10JS不能重编译或更名。本地dist/合成preview/bootstrap/API模拟不得进入生产镜像。正式release-patch和完整315清单须由Web代理另行冻结SHA，再由root与独立审查绑定。

候选Image Config保持父镜像Config、RootFS旧层前缀不变，不下载/安装依赖。实际容器仅目标不可变image和精确已冻结的Compose归属标签随发布变化，原环境/命令/端口/挂载/网络/策略及其余有效配置保持；不得以配置重建为由放宽保护。

## 4. 控制器、候选与实际隔离验收

复用既有已审生产控制器的归属、完整七门禁、固定镜像切换/受保护回退和完整Mounts保护原语，针对本轮双组件/230源/315静态重新冻结计划；不把QA-only控制器当发布器，也不复用旧prepared/progress。控制器/每项支持文件/输入SHA/父镜像/本地验证证据/正式Web元数据全部绑定，专属新发布目录及候选/回退标签，不移动共享标签。

prepare只准备固定旧镜像回退、离线派生候选和隔离验证，不迁移或切换业务。实际Backend候选必须禁网、只读、无业务生命周期/依赖构造/线程/数据库/文件写/子进程，检查完整230源/202OpenAPI/schema/340Settings有效配置、原功能与事实/JSON守卫、partial安全计数和无有效修改固定失败、原v1/金融/删除屏障，并验证真实合成DOCX/PDF。不得实例化会迁移/修复数据的仓库；所有七类副作用计数0，不使用真实模型。

实际Web候选必须逐项核对315清单、15patch及全部旧路径/模块URL/正文保留、Image Config、NGINX和读取权限。新patch严格0644、公开目录0755；全部旧文件模式按第7节实际模式基线精确继承。私有控制/环境文件0600及服务器发布根0700，不能将私有模式传播到公开文件，也不对线上原目录递归chmod。切换前必须用固定Web候选启动隔离真实NGINX及可控健康stub，实际读取登录/普通/模拟/笔试/简历优化/构建路径和15patch公开文件，HTTP200且正文SHA等于预期；候选工作进程可读全部315文件及NGINX，实例清理有证据。只做源码/hash或语法检查不够，不连接真实模型/账号/生产任务。

## 5. 完整七门禁、固定顺序与等待

preflight、每个Backend/Web实际切换前和每个回退前，必须在同一发布排他锁内重复完整七门禁，门禁代码绑定SHA且以实际旧Backend父镜像执行，避免Python旧默认image绑定问题。完整保护普通live/recent preparing、页面/准备租约、连接/工作桌面发布端与令牌/音轨、未完成文字/截图/远程采集、Mock活动阶段/生成控制租约、资料处理/删除/对账工作、有效未付订单/最近回调及CN optimizer queued/running/未知状态/usage。

只有有效真实保护活动非零的`protected_user_work_cutover_deferred`允许保留当前安全状态等待；无变化时不反复通知。unknown/readfail/字段缺失/非法/扫描超限/样本过期/零活动但进程失败或源码/配置/控制器/归属漂移必须停止自动切换并报告；不能静默当忙碌重试。不得结束面试/优化、清理活动/租约、改TTL/样本或放宽门禁。门禁是瞬时快照，不能承诺绝对零竞态或零用户影响。

全部通过后只按固定Backend→Web顺序切换，各自专属不可变镜像与已冻结有效Compose。若Backend已切而Web前出现新活动，维持已验的部分发布并等待；恢复先核对本次归属、真实镜像和结果，跳过已完成组件，不重复重启。无DDL/配置/模型调用/其它组件重建。

仅当Backend切换后IP实际变化且当前代理须刷新DNS，可沿用旧机制对现有Web/Admin先`nginx -t`再reload；IP未变不reload。此窄代理刷新不改配置字节/镜像/容器身份/启动身份，不构成Admin功能发布；Web本身的目标切换仍是独立受保护步骤。语法失败或归属漂移停止报告。

## 6. 受保护归属回退与独立验收

切换或验收失败，先确认目标仍归属本次发布，再在完整相同七门禁空闲时按Web→Backend顺序恢复本次冻结旧镜像/原有效配置。新用户活动、unknown/readfail或归属漂移时停止自动恢复并报告，不能绕过保护回退。保留原表/任务/资料/用户已发生账本及新结果，不删数据、不撤销真实消费、不回放用户任务。已部署标记须核对真实结果，不能重复重启或沿用其它目录归属。

独立verify须检查实际两目标固定镜像/容器与发布归属、running/Backend healthy/重启0、完整230源/202schema/340Settings/有效配置、315静态及原功能/全部非目标/共享标签保持。至少7类公共GET（健康、登录、普通/模拟/笔试、简历优化、构建）200且HTML/build/新资源SHA相符；匿名optimizer能力和导出仍401/private,no-store。safe-edit/失败消息/计数/wire与原金融边界由固定候选离线合成探针和已验收本地证据证明，不代用户登录生成、访问历史正文或产生真实费用。

短时观察只统计新目标实际覆盖窗口内脱敏ERROR/traceback/HTTP5xx与固定诊断计数，注明覆盖秒数/是否截断，不导出原始日志/用户或会话标识。异常据实际归属/活动保护处置，不冒称长期P95、全部真实简历或绝对无用户影响。最终更新12.1–12.5、[发布记录](../../../docs/releases/cn-resume-optimizer-safe-edits-20261018.1.md)与逐场景，之后通知用户正常账号自测。

生产证据统一`artifacts/cn-resume-optimizer-safe-edits-20261018-release/`；拟服务器目录`/opt/offersteady/releases/20261018-cn-resume-safe-edits-1`，以root实际核定为准。服务器私有配置/原日志/源资料不进入本地证据。当前尚未发布，候选/切换/验收完成只能按后续真实结果记录。

12.1只读基线部分已取得：root新生产冻结证据artifacts/cn-resume-optimizer-safe-edits-20261018-release/current-baseline.json，SHA5a670a02c4484dde6d01056ed1908aa3edb0680ee80df52db412add3043e748a；除atMs外与已验收QA基线每个完整字段相同，实际229源/202schema/340Settings/305静态/NGINX/全部非目标、Backend healthy/重启0保持。此事实只完成12.1的基线部分，root独立strict实施GO尚待记录，12.1暂不勾选，不代表候选/发布完成。

## 7. 首次prepare权限误检与dir2窄修（待root独立GO）

dir1实际Web候选`sha256:2124eee829453776d6191b669c29a28c06f83a011bb6b8461432fefd1393463d`完整315内容/NGINX/Image Config/旧层检查已通过，但prepare在`candidate_public_file_permissions_failed`停止，未切换、未调模型，尚未完成权限与隔离NGINX验收。`actual-public-mode-diagnostic.json`证明316文件全部nginx可读，只有8个继承AppleDouble元数据普通文件0755，不能据此称线上正文不可读。

root只读实际旧Web029e84e0…/20d6a03a…的`actual-baseline-public-modes.json`（SHA-256 `ae9835e7ebdfa2c449c38f06fc5cf7281249edd5c88b773051020908a78777bb`）确认原305静态+NGINX全部306可读，原10目录0755，精确以下8个原元数据文件0755，其余原文件及NGINX均0644：

- `._assets`
- `._media`
- `._seo`
- `assets/._brand`
- `assets/._mock-interview`
- `assets/._payments`
- `assets/._support`
- `media/._homepage`

本节只修验证器预期，不改候选或线上旧权限。dir2 SHALL 绑定完整实际模式基线SHA/原20d6身份及原文件内容SHA，要求这8固定原路径逐项保留0755，其他原文件、全部15新patch及NGINX严格0644，全部10公开目录0755，完整315+NGINX全部316仍须nginx用户实际可读。不得通用接受“0644或0755”、只检查可读、忽略未知/多缺路径或额外可执行文件，也不得chmod/删改旧资产。公开输入新patch仍文件0644/目录0755，私有0600/0700保持。

dir1控制器/输入/payload/prepared痕迹与失败证据完整保留；使用独立controller-v2/payload-v2及服务器`/opt/offersteady/releases/20261018-cn-resume-safe-edits-2`、专属tag/token/归属，不复用旧progress。Backend仍固定f6dbe8fd…；Web直接复用上述2124eee8…不可变候选，不再build、不改15patch/build标识或产品源。新prepare重新全部检查实际原组件/模式/源静态/Config/旧层、禁网Backend、逐项模式和隔离真实NGINX，首轮部分检查不能代替新实际验收。新增回归覆盖精确8路径0755、其余原/新文件及NGINX0644、目录0755和316可读，未知/多缺路径/正文0755拒绝。root独立strict/工具GO前不实现，12.2仍pending；原七门禁、漂移停止/归属恢复及无产品/费用/DDL/配置/模型/Git边界保持，此发布工具窄修不需用户重复批准。

## 8. dir2隔离探针传输修正（不改产品或验收范围）

dir2原306/候选316精确模式与Backend230/202禁网副作用0通过，隔离NGINX在任何HTTP前因Docker internal网络没有可用publish映射，于直接读取Ports[80/tcp][0]发生TypeError而停止，未切换、无模型。独立只读诊断仅在内存将访问地址转到同一自建internal网络的候选私有IPv4，原完整25项（23个200且SHA、2个404）全部真实通过并清理2容器/网络；证据actual-isolated-nginx-private-ip-v2.json SHA 690ad7c6b6ce9047e22d711a94dd7e1cff4e617fa687a175ffa01d00ff5a8fc6。这是诊断，不代替新prepare通过。

使用独立controller-v3/payload-v3及服务器/opt/offersteady/releases/20261018-cn-resume-safe-edits-3，原dir1/dir2所有输入与失败证据保留。仅隔离NGINX探针取消publish，确认候选仅连接本次精确internal网络且IP是私有IPv4后，由服务器请求此IP:80，Host和完整25项HTTP/SHA、固定stub/Config/NGINX/资源读取/归属清理都不变；地址不输出，不连接生产网络或修改NGINX。两固定候选/15patch/精确原mode/七门禁/切换恢复/无模型无业务写全部保持。新增最小回归覆盖Ports为空仍可测、错误网络/非法IP拒绝、无publish；新prepare须从头实证，12.2仍pending。

## 9. dir3实际完成与边界

实际服务器目录`/opt/offersteady/releases/20261018-cn-resume-safe-edits-3`；控制器SHA `c6dce7b3385064dc3b4e3384be1b346553cbafa329c8e318234006db741ca62f`，输入SHA `9aa65c2d7e0ed3b975183c1ca54f2afedde4960cdc5bae5c87cb2a2733100155`。115工具回归/独立复跑通过；原dir1/dir2输入、失败候选及本地dc869f66…证据保持。实际prepare重新通过Backend230/202/schema/真实DOCXPDF/七副作用0、原306/候选316精确模式、25项隔离NGINX（23正文SHA200+2指定404）和严格清理。

2026-10-18北京时间06:48:36.013部署、06:49:05.768独立verify通过。Backend容器`50bcb76f5b05603bcd3071bbd622a95a6a91009c5837fbc9f88cb67c1b560dd3`运行固定f6dbe8fd…，Web容器`88ae70c9fd1bdf39dd5f7b2f15b54266ca058e23b843ced2d24e22ba15eaaf38`运行固定2124eee8…；deploy/verify/独立只读快照归属一致。完整230源、202完整schema、340Settings有效摘要、315静态/NGINX、6非目标与共享tag全部核对保持；Backend healthy、两目标重启0。两次线上验收各19项：17个200（含10新资源逐SHA）和2匿名401/private,no-store。

实际重复七门禁均有效空闲，最后sampleAge24945ms；本次未发生busy/部分发布/回退/代理reload，相关等待、恢复与漂移拒绝由合成工具回归覆盖，不能写成生产执行。短时观察Backend114.289秒/404行、Web79.385秒/179行，未截断，ERROR/traceback/HTTP5xx/固定失败及未知诊断均0。没有本次额外模型/真实测试任务钱包写入、DDL/环境/费用/Git/Global/助手/Admin重建。此结果不代表完整180秒、长期P95、所有真实简历成功或原用户历史任务已成功；由用户正常账号测试效果。最终独立记录为`independent-audit/final-release-review.json`和`root-final-runtime-review.json`。
