# 国服简历优化失败诊断 Backend 热修复生产追加规范

## 最新授权与范围

用户在[20261018.3本地修复验收](../../../docs/releases/cn-resume-optimizer-local-20261018.3.md)后，明确要求继续优化开发并在完成后部署上线。授权同时包含此前提出的一次纯合成简历真实 Provider 验证。9.x本地阶段的“未上线/未调用真实模型”是已执行历史，必须保留；当前生产热修复是否完成只依本追加下的实际证据更新。无需重复请求已有明确授权。

状态：已完成实际dir2发布与独立验收；下述规划、门禁和尝试历史保留，最终结果见末尾。允许范围仅 CN Backend：以当前预期实际运行镜像 `sha256:995ae331be9879d53309578f05056e081029e1018cc62ed89f45b81df5fcea2f` 为待重新确认的固定父镜像，发布本地已验收的 Provider、Service、Repository 三文件及新增 diagnostics 一文件。四个路径均位于 `apps/backend/app/services/`，文件名前缀 `cn_resume_optimizer_`。完整已发布228输入应为225不变、3项既有修改和1项新增，候选229项；若有受准许的合成定位修正，必须重验并重新冻结这四项之内的最终输入，不直接沿用旧测试SHA。

本次 MUST NOT 改 DDL/迁移、环境/除Backend固定image字段外的Compose有效配置、依赖、模型配置/预算/并发/超时、费用/会员次数、Prompt、Web/NGINX/static、Global、桌面助手、Admin、资料worker或其它业务，不提交推送Git。功能仍为会员每日3次/其余100积分、单一JSON严格兼容和全部事实守卫。既有 0054 不重跑、资料/旧账本/原失败任务不改写，不代用户重试或扣费。

## Requirement: Refreeze the actual Backend and protect every non-target

准备前 MUST 只读重新冻结实际 CN Backend 容器身份、不可变镜像、image Config、完整有效Compose/环境/标签/HostConfig/挂载/网络、启动/健康/重启信息、228项完整源/Prompt/迁移/资产及202条完整API路径和schema。旧目录、`current`标签、健康版本字符串和旧容器快照不能代替本次实际运行状态。预期父镜像、输入、有效配置或归属不符 MUST 停止，记录漂移后由root查明，不自动扩大文件清单。

原正常/模拟/笔试、钱包/支付、鉴权/状态读取、预取/语音/助手清单和已上线简历功能路由 MUST 保持；除批准四文件内的诊断和传输兼容外，旧方法及配置保持。Web `sha256:20d6a03a6acdc923f02cc786af2cdd862599b4e65ef1d2dbc9fd77be7c163610` 仅为待核对的非目标预期，必须记录实际身份/静态/NGINX摘要，并与其它非目标组件一起在完成后核对未变。生产私有配置只在服务器0600保存，返回本地仅安全摘要和SHA，不输出密钥或环境内容。

## Requirement: Fixed four-file candidate and side-effect-free probe

候选 MUST `FROM` 本次确认的固定实际 Backend 镜像，仅复制批准四文件，不重新安装依赖或修改 image Config/环境。绑定输入、实际父/候选镜像、控制器/七门禁/探针/验收支持文件和本地回归SHA，使用本次独立发布目录、专属固定候选/回退标识及排他锁，不覆盖共享标签。

实际候选 MUST 在禁网、只读根文件系统、不进入应用生命周期、不解析真实业务依赖、不构造会迁移/修复用户记录的仓库、不启动后台线程条件下，验证229完整输入、202完整路径/schema/旧保护方法/运行配置、固定诊断/原公共wire/会员3次100积分规则、严格JSON包装正负例和事实守卫。网络/数据库/写文件/线程/子进程/依赖解析/生命周期副作用计数须为0。探针和控制器合成回归通过后，才可进入允许的真实Provider验收或生产切换；原283项本地回归不能代替实际候选验证。

## Requirement: One bounded authorized synthetic Provider diagnosis

真实Provider验收是上述禁网探针之外的单独、明确授权步骤。先复用完整七个只读门禁确认无受保护工作，使用候选的直接 `CNResumeOptimizerProvider.generate` 与原服务器私有模型配置，只发送经审阅、显式标记synthetic的简历及可选合成JD/岗位。输入 MUST 全部在固定合成用例中定义，使用虚拟姓名/无效域名联系方式，不取用户上传、OSS、任务快照或真实资料，不启动app/worker/仓库，不创建job、usage、账本或面试，不访问钱包和真实用户资料。

初次诊断最多1次真实请求，不自动重试；沿用原90秒/6500 token/单请求限制，仅返回通过与否、固定reason/stage、时长及安全计数。不得输出API密钥、原响应、Prompt或私有配置，也不能把合成结果称为原失败任务根因。若失败，只能根据固定原因，在四文件内的既有批准严格兼容或实现缺陷范围修正，补充对应合成回归和AI eval、独立审查、完整适用重测并重新冻结候选；不得放宽事实守卫、修补JSON、跳过schema或改Prompt来强行通过。

完成有依据修正后可针对同一明确合成用例进行1次真实验证，前面同样重读七门禁；不得盲目追加请求。若仍失败、出现范围外原因或需要改变事实/Prompt/模型策略，停止自动发布并报告具体固定原因和所需处置，保持当前服务。仅成功的合成Provider验证不等于真实用户端到端、格式导出、长期质量或P95验证，不可冒称。任何合成修正后的来源/候选SHA必须与最终部署完全绑定。

## Requirement: Seven complete gates and a Backend-only cutover

preflight、任何Backend实际切换前及回退前 MUST 在同一发布排他锁内紧邻动作重复此前生产已审查的完整七门禁，完整保护普通live/recent preparing、页面/准备租约、活动桌面/连接令牌/音轨、未完成文字/截图/远程采集、Mock阶段/生成/控制租约、资料/删除/对账任务、有效未付订单/最近支付回调及CN optimizer queued/running/未知状态。只输出聚合固定计数。不得替换为单一live_interviews计数或省略金融/optimizer门禁。

保护活动非零且门禁可用时按 `protected_user_work_cutover_deferred` 维持当前服务等待；未知状态、读取失败、扫描超限、非法字段/元数据、容量样本过期或归属/配置漂移须作为不可用/漂移停止自动切换并报告。不得终止面试、取消真实优化、清理任务/租约、修改TTL/样本或放宽保护制造空闲。

完整通过后，仅使用固定Backend候选与冻结原有效配置切换Backend；无DDL、无环境新增/覆盖、无Web或其它组件重建。仅当Backend切换后IP实际变化，允许沿用既有机制，对现有Web/Admin容器先执行 `nginx -t` 成功后reload以刷新DNS；不重建容器、不改配置内容/镜像/启动身份，记录固定proxy-refresh聚合。IP未变化不得reload，语法失败停止并报告。此窄例外不代表Web/Admin功能或部署变更，其余非目标行为完全保持。已切换标记存在时先核对真实归属和结果，不能重复重启。活动门禁为瞬时快照，不代表绝对零竞态/零影响。

## Requirement: Owned rollback and independent truthful acceptance

候选或切换验收失败时，先确认当前Backend仍归属本次发布；固定回退至本次确认的旧 `995ae331…` 镜像及冻结原配置，回退前仍重复相同七门禁。有新用户活动、未知/读失败/漂移时停止自动回退并报告，不绕过保护、不结束活动。回退不得删除新失败诊断/任务/账本、修改用户数据或撤销真实消费；新诊断只为原JSON payload附加元数据，旧应用继续兼容。

切换后必须独立verify：实际固定镜像/容器归属、running/healthy/重启0、229源/202路径/schema/有效配置完全匹配；全部非目标组件身份、Web静态/NGINX保持。公开健康与原/新页面可访问，匿名optimizer能力/导出仍401及private,no-store；owner消息映射/旧任务回退/内部诊断不出wire由候选合成探针与本地HTTP证据验证，不代真实用户创建或读取正文。

短时观察仅输出新容器窗口内ERROR/traceback/HTTP5xx及固定诊断聚合计数，不输出原始日志或会话/任务标识；注明实际覆盖秒数，不承诺长期P95或所有用户无影响。最终据实更新任务10.1–10.5、[待执行发布记录](../../../docs/releases/cn-resume-optimizer-hotfix-20261018.1.md)和逐场景。证据目录统一 `artifacts/cn-resume-optimizer-hotfix-20261018-release/`；拟服务器目录 `/opt/offersteady/releases/20261018-cn-resume-optimizer-hotfix-1`，只有root实际核定后才记录为已使用目录。

## 首次热修复尝试及挂载数组顺序的完整字段规范化

第一次实际prepare成功，固定候选 `sha256:6f2a53f55ac6343c983234fedde62bd46432a1087c75705425c267971bf3d581`，实际禁网229源/202路径/schema/真实合成DOCX/PDF和七类副作用0通过，当前Backend仍原995ae331…且健康重启0。随后preflight以 `non_target_identity_or_configuration_changed` 停止，未调用真实Provider、未切换生产；完整保护未被绕过。聚合只读差异定位为PostgreSQL容器Mounts摘要不一致，容器/启动身份、Config、HostConfig和完整网络摘要相同。此时完整原值是否仅数组排列仍待核对，不能据摘要差异断言数据库挂载实际变化，也不能提前写成已确认Docker顺序问题。

只有root在服务器只读确认前后Mounts的完整字典多重集一致、旧新原始摘要能由同项排列复现后，才允许采用以下窄工具修正：仅对 `docker inspect` 的Mounts最外层数组，按每个完整条目的canonical JSON稳定排序后计算/比较。条目的全部字段和值、重复条目及其数量 MUST 保留，嵌套数组顺序保持；不得投影Source/Destination等局部字段、删字段、去重、忽略实际增加/删除/值变化，HostConfig原结构和其它所有保护继续保持。Mounts摘要与运行时同值比较采用相同规范化语义；任何真实差异仍fail closed。

修正前 MUST 用合成回归证明：仅排列变化摘要相同；任一已有/未知新字段、条目增删或重复数量改变仍被拒绝。不得原地改已prepared的控制器、payload、基线或旧结果；拟使用 `/opt/offersteady/releases/20261018-cn-resume-optimizer-hotfix-2` 新目录及专属标识，重新冻结实际完整基线/私有上下文、四业务源/控制器/支持SHA，并完成新回归、独立审查和实际候选prepare/无副作用探针。旧候选成功只保留为尝试1事实，不能冒充修正后控制器已验收。七门禁、一次Provider marker及成功receipt/固定回退/非目标保持规则完全沿用；本修正属于已授权发布工具故障处理，不改变产品或需重复请求用户已有授权。

## 挂载顺序误报已确认及新冻结（后续只读证据）

root随后通过服务器只读完整值核对确认：全部7个非目标的Mounts完整条目多重集均与原基线相同，未导出挂载路径/配置；PG两条挂载当前原序摘要d6d61…，稳定排序摘要229772…，恰与preflight报出的不同摘要相同。故本次是inspect最外层排列不稳定引起的工具误报，没有证据表明PG挂载实际改变。前节“待核对”描述保留为当时事实，当前结论以本节证据为准。

root已批准完整 `canonicalMounts` 排序修正和新目录2，明确Source、Destination、RW及所有现有/未知字段、完整HostConfig和重复数量仍参与保护。新基线v3 SHA-256为`00e571478feea69cfb0c14099db86f79c653faf17c4aae0b9186457872f86943`；独立递归比对v2，除读取时间atMs与PG mountsSha256改为该稳定摘要外，所有原字段保持。证据`mount-order-proof.json`及`current-baseline-v3.json`位于本次发布artifacts。新controller-v2及dir2须完成修正回归/独立审查/实际prepare后才允许继续，旧停止/候选/控制器/input包完整保留；未执行真实Provider或生产切换。

## 实际生产完成（dir2最终证据）

最终仅Backend于北京时间2026-10-18 05:07:33.546切换，05:08:35.669独立verify通过。实际容器b955c33e…/镜像6f2a53f5…、controller e5ad4d31…、input e6c6bc42…、v3基线00e57147…均与审查绑定；七门禁全0/exit0且容量样本23.508秒，原配置/202完整schema/229源、七非目标与305静态保持。IP未变，未执行Web/Admin reload或任何非目标重建。本热修复无DDL/环境/费用/Prompt/Git或Global/助手变更。

一次固定纯合成直接Provider19335ms成功，requestCount1，receipt及先消费marker已核对；无job/usage/账本/资料/真实用户验收和额外模型请求。7公开200/原HTMLbuild SHA、2匿名401/private,no-store通过；最终新Backendhealthy/重启0，短时实际Backend107.969秒/Web87.266秒各ERROR/traceback/HTTP5xx0、固定诊断空/unknown0、未截断。dir1停止与完整顺序证明保留；实际发布、verify、观察和独立可复算final-release-audit证据见[生产记录](../../../docs/releases/cn-resume-optimizer-hotfix-20261018.1.md)。不能据一次合成成功认定旧用户任务精确原因、所有真实简历或长期模型/性能已验证。
