# 国服简历优化 20261018.2 生产发布追加规范

## 授权与历史边界

2026-10-18 用户在本地开发、自测和页面简化交付之后明确要求：“这个功能上线到国服吧。我这边测试下效果”。此授权允许把已验收的国服简历优化 20261018.2 增量发布到国服 Backend/Web，并仅为此启用 CN 专属功能开关。原记录中的“仅本地”“未上线”描述对应当时已执行事实，须保留；它们不再代表本次发布尚缺用户授权。仍未授权 Git 提交/推送、国际服、助手、Admin 或其他功能/收费改动。

产品规则保持 [合同 v2](contract.md)：有效时间会员按北京时间每天免费 3 次，非会员及超额每次 100 积分且仅在付费操作前确认；原普通/模拟/笔试、支付、钱包、收音、资料、已发布性能优化和 Global 政策不变。页面保持已验收的简洁版本。实际模型质量由用户上线后使用自己的正常账号验证；发布验收不得调用真实模型、创建真实面试、代用户扣积分或使用真实用户内容作为测试夹具。

## Requirement: Refreeze actual running CN component baselines

发布 MUST 重新只读核对 CN Backend/Web 各自实际运行容器、不可变镜像 ID、健康/重启次数、完整有效 Compose/环境/挂载/网络配置及原标签归属。此前本地绑定的 Backend `sha256:4c305868ca6799cb7b8a69afd691f2e2e966785dfce827a0e04c51fa431fd656` 和 Web `sha256:695959e95ef1ca20367c62333acd42e6aaf05df5c16692da039d8ca873cc0f2c` 只能作为待重新确认的预期，不能用 `current`、健康版本字符串或旧目录替代实际运行镜像。

完整 Backend 输入、旧 HTTP 路由/OpenAPI/schema/保护方法、Prompt、助手清单和既有鉴权/状态/预取行为 MUST 保留。候选仅允许已验收的 6 个旧 Backend 输入（5 个最小接入文件及 pyproject）和新 CN 源/中文 Prompt/导出资产/0054 迁移，依赖必须离线固定版本 ReportLab 4.4.9 及已冻结 wheel。CN 开关改为 true 是唯一批准的既有运行环境配置增量；默认代码仍为 false，Global 开关、模型/供应商、计费和其他配置保持。

实际 Web 所有静态文件 MUST 逐项冻结，包括旧 HTML/公开内容/价格/SEO/媒体/错误页/旧 hash 资源，NGINX 仅允许在现有工作台精确路由 allowlist 中，在 `/library` 后增加字面量 `|/resume-optimizer`，以支持直达/刷新新页面；其他配置和原 image Config 保持。只追加经实际构建审查的简历优化所需 hash 资源；`index.html`、`guide.html`、`terms.html`、`privacy.html` 仅允许改新 module URL，公开正文保持；`offersteady-build.json` 仅更新新构建标识。本地完整 dist 不得整包覆盖或删除线上文件。原已启用模拟面试及普通/笔试导航和完整旧路由 MUST 保留。

任何来源/镜像/配置/控制器/支持文件漂移 MUST 停止自动切换，先记录并报告；不得自行放宽清单、套用旧共享标签或把 Global 整包覆盖 CN。

## Requirement: Immutable candidate and no-write probes

发布输入 MUST 绑定控制器、支持文件、每项候选 SHA-256、实际父镜像、验证结果和实际构建资源清单；prepare 仅固定回退标签/准备私有文件/构建候选及运行只读探针，不切换应用。候选镜像 MUST 派生自实际运行父镜像的固定层；不重新安装未冻结依赖，不更改无关 image Config。

完整导入/OpenAPI/旧路由探针 MUST 在禁网、只读文件系统和不启动业务生命周期/线程的条件下运行，验证旧输入/函数/完整路由和 schema 不回退、CN 新能力已启用且 3 次/100 积分合同正确；不实例化会迁移或修复真实数据的业务仓库。构建与探针结果须和前述本地 147 后端/480 网页及格式验证区分记录，不得把旧自测直接等同于实际候选验收。

## Requirement: Protected work gates before every mutation

preflight、迁移前、每个 Backend/Web 切换前及任何回退前 MUST 在同一发布排他锁保护下独立重复只读门禁；不依赖候选健康或候选业务构造器。门禁输出只能是固定聚合计数，不得输出用户资料、会话标识、Redis key、私有环境、模型 payload 或原始日志。

金融补充门禁仅保护有效期内的未支付订单和最近 120 秒未完成支付回调，并拒绝未知订单状态/读取失败；过期未支付旧订单不阻塞，也不在此清理或改写。

保护范围 MUST 包含普通面试 live/recent preparing、活动/准备页面租约、连接或工作中的桌面发布端与有效连接令牌、近期音轨、未完成文字/截图/远程采集、模拟面试活动阶段及控制/生成租约、资料处理/删除/对账工作和任务。增加可在固定旧 Backend 镜像运行的 CN optimizer 门禁，保护新表 queued/running 及未知状态，并检查表缺失与已应用迁移的一致性，读取失败关闭门禁；发布后的部分状态和回退也使用这一保护。

任一保护计数非零、字段缺失/非法、未知状态、读取失败、扫描超限或样本过期 MUST 视为不可切换。仅在 `protected_user_work_cutover_deferred` 且实际有效保护活动非零时保留当前安全状态等待；未知状态、读取失败、非法元数据、扫描超限、容量样本过期或零活动但进程失败属于 `protected_work_gate_unavailable`，必须停止自动切换并通知处置，不能当作正常忙碌静默重试；不得终止真实用户面试、清理任务/租约、伪造空闲、修改 TTL 或放宽保护。门禁只是发布前的当前快照，不构成零竞态或生产零影响保证；须尽可能紧邻每个实际切换重新读取，并保留已有页面/收音租约保护。

## Requirement: Additive migration and fixed ordered cutover

只有完整只读 preflight 通过后才允许在发布锁内执行 0054 additive 迁移，使用受限连接/锁/语句超时。仅创建两张 CN 表和精确扩展账本 charge/refund 约束，保持未知旧合法 kind、符号约束、不可变 trigger 和历史行；不执行 destructive down。迁移完成后再次门禁，先 Backend 后 Web，各自使用专属固定镜像 overlay，不重指共享镜像标签，不更新其他组件。若 Backend 已更新后又有保护活动，保留可验证的部分发布并等待，恢复时核对归属并跳过已切换组件，不重复迁移/重启。

新服务须满足 running/healthy/restart-zero、完整来源/路由/schema/有效配置相符；原 Web 静态资源与原 NGINX 除上述唯一新路由字面量以外的字节保持，非目标容器身份及原环境/挂载/网络不变。Backend IP 改变时只在确有需要时刷新已有代理配置，不重建代理/Admin。

## Requirement: Owned recovery and independent acceptance

切换或验收失败后的恢复 MUST 先确认失败组件仍属于本次发布，再用固定旧镜像和冻结的原配置执行相同完整只读门禁。出现新活跃工作、未知状态、归属漂移或门禁不可用时停止自动回退并报告；不得绕过保护恢复。允许回退时按 Web 后 Backend 顺序恢复固定旧镜像，保留 additive 表和已产生的新账本/优化数据，不删用户数据、不撤销真实扣费。

已部署标记存在时 MUST 验证真实容器/镜像/完整结果和归属，不能重复重启。完成切换后运行独立 verify：确认公开健康/登录/原路由和新页面可用、匿名 CN optimizer 能力及导出仍 401/private,no-store，原模拟面试能力/导航存在，完整旧资源可读取，新页面直达/刷新返回正确入口且其余原 NGINX 路由保持，新 API 的最小能力合同由隔离只读探针验证。短时间日志检查仅输出脱敏 ERROR/traceback/HTTP 5xx 计数及观察窗口，不能声称已经验证真实模型质量或长期 P95。

产物与门禁/prepare/preflight/deploy/verify/脱敏统计证据保存在 `artifacts/cn-resume-optimizer-20261018-release/`，服务器私有配置留在服务器。完成后由 root 根据真实证据更新生产记录、任务 8.1–8.4 与逐场景结果，再通知用户测试；等待活跃工作期间不重复发送无变化通知。

## 发布准备/恢复事实及第三次尝试门禁（2026-10-18 追加）

第一次准备在实际 Web Compose 只有 build、没有显式 image 的历史形态上报错，尚未迁移或切换生产组件。已补严格兼容：仅允许实际 CN Web、非空 build、运行引用 compose-web 且该标签不可变 ID 等于原运行镜像；显式 image 和完整配置保护保持。

第二次发布已执行 additive 0054 并切换 Backend/Web；随后公开验收抛出 HTTPError；原异常未保存具体路径与HTTP状态，不能补写为某一路径已观测403。随后对同固定候选进行隔离 NGINX 实测，确认 index.html/default.conf 被安装器统一设置为0600，工作进程无法读取，6个应用/构建路径均403；据此推断原公开验收失败与该权限缺陷一致。该失败不得未经证据归因于浏览器缓存或伪称未更新线上。已通过原固定镜像、完整活动门禁及归属核对按 Web→Backend 恢复。恢复后公开登录/原面试/模拟/笔试路径200，新功能路径404（符合旧版本），新 additive 表保留，未删用户数据。

恢复后的实际基线容器分别为 Backend `b7a44f78cc89e271700052e70f4f34f35dabfda2bcdadf41e592624568e11bd7`、Web `f9e5cb7ab13a56dfb011711d6695571ac0af05097e6179756dc4b91ee5eb5c9a`，固定镜像、216旧源/294静态/原NGINX/195旧完整路径及环境/HostConfig/挂载与原基线保持。第三次尝试 MUST 重新冻结这些真实容器和当前 Compose，不复用失败的 prepared/progress；使用新发布目录和专属构建/候选/回退标签。

公开静态 payload 文件及新 default.conf MUST 为0644，公开目录0755，不得把私有控制文件的0600策略传播到 Web 文件；服务器私有配置仍0600，私有发布目录仍0700。控制器 prepare MUST 验证输入模式并保持复制模式，在候选镜像内再次核对全部公开文件/目录和 NGINX 读取权限。它只修正新输入/新候选，不对原线上目录递归chmod。

第三次实际切换前 MUST 用固定候选 Web 镜像启动隔离 NGINX 实例、绑定可控健康 stub，不接真实模型或用户账号。至少实际 GET `/login`、`/app/resume-optimizer`、`/app/mock-interviews`、`/app/interviews/new`、`/app/written-exams`、`/offersteady-build.json` 均200且正文SHA等于候选 index/build，并保存候选镜像ID、检查结果和实例清理证据。静态文件SHA或NGINX语法通过不能代替此真实读取验证；验证失败不得盲目重试线上切换。通过后仍须重新执行完整 preflight/逐组件活动门禁。

本节记录了已发生的生产切换和恢复；编写本节时第三次候选尚未准备，后续状态见下方实际候选追加。当前实际状态仍以 root 后续冻结与独立 verify 证据更新。证据：`production-restored-snapshot.json`、`public-paths-restored.json`、`isolated-nginx-routes-v4.json`、`runtime-before-attempt3.json`，均位于本次发布 artifacts 目录，原失败结果保留。

## 第三次实际候选准备与权限验证已完成（切换结果另记）

实际 prepare 固定候选 Backend `sha256:995ae331be9879d53309578f05056e081029e1018cc62ed89f45b81df5fcea2f`、Web `sha256:20d6a03a6acdc923f02cc786af2cdd862599b4e65ef1d2dbc9fd77be7c163610`。实际候选探针228项输入、202条完整路径/新增7条、旧schema保持、真实合成DOCX/PDF通过，七类副作用计数均0且未进入生命周期。nginx用户禁网只读权限探针17路径通过。

同固定Web镜像的真实隔离NGINX实际执行17个GET（6个新旧应用/构建路径及11项新资源），全部200且正文SHA逐项等于冻结候选；index/default.conf均0644且与原镜像一致，NGINX SHA正确，隔离实例已删除，无真实模型调用。独立审查重新核对这些绑定并保存 `independent-actual-candidate-audit-v3.json`。本段只证明实际候选准备/读取验证，不能提前代表本次生产切换、独立verify、短时错误统计或用户生成测试通过。

## 第三次生产切换及独立验收完成

北京时间2026-10-18 04:14:12.465完成固定Backend→Web切换，04:14:54.740独立verify通过，运行镜像分别为995ae331…/20d6a03a…，与实际prepare相同，deploy/verify容器身份一致。最后完整7门禁均通过，旧钱包trigger与其他约束保持，历史行未修改；7公开GET200及冻结HTML/build SHA、2匿名优化API401/private,no-store均核对通过。短时新Backend148秒/Web114秒ERROR、traceback、HTTP5xx计数均0；非目标组件和既有配置保持（仅CN新开关启用）。

最终逐场景证据见[验收记录](verification.md) C43–C46与本次发布artifacts中的`independent-final-release-audit.json`。实际用户生成/模型质量和长期指标仍待用户测试；第二次失败与恢复事实保留，不作“全程零影响”承诺。本次未更新Global/助手/Admin或提交推送Git。
