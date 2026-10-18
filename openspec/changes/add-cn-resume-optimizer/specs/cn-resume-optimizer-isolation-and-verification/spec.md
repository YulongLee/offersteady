## ADDED Requirements

### Requirement: Independent bounded durable execution
国服专属开关 SHALL 默认关闭，显式启用且模型配置有效才接受工作。任务 SHALL 持久化 queued/running/completed/failed/cancelled，最多每账号 1 个未完成、全服务 8 个未完成和 1 个模型请求，独立执行器/客户端、90 秒 Provider 超时及 15 分钟排队上限。中断或过期 MUST 可见失败并退款，不盲重放模型，不占面试执行池。

#### Scenario: Disabled or another region
- **WHEN** 国服开关关闭或运行国际服
- **THEN** 不启动 CN optimizer 工作，现有区域权益和其他功能不变

#### Scenario: Full capacity or interrupted generation
- **WHEN** 达容量上限、模型超时或进程恢复发现过期任务
- **THEN** 有界拒绝/失败且未交付原路退还，不无界排队或重复调用

#### Scenario: Interview workload is active in synthetic test
- **WHEN** 合成面试与优化同时运行
- **THEN** 各执行路径独立，面试取消/处理语义保持，不借用优化队列

### Requirement: Slow nonfinancial save does not block existing wallet admission
优化状态操作 SHALL 由独立 owner 锁串行化；只有金融变化再按固定顺序获取既有 billing-user 锁。已完成稿编辑/另存执行 OSS/Parser I/O 时 MUST NOT 持 billing-user 锁，仍须保持源行共享锁、revision 和删除屏障，且不得改变旧钱包实现。

#### Scenario: Slow save-as and normal wallet usage
- **WHEN** 同一账号的另存回调在合成慢存储上等待，同时普通回答通过原钱包预留积分
- **THEN** 原钱包操作无需等待另存回调即可完成，另存仍保持幂等、revision 和源删除安全

### Requirement: Owned access and derived deletion
全部接口 MUST 验证登录及 owner，列表不含正文。任务或源简历/JD 删除 MUST 同事务阻止读取/完成、取消未完成工作并清空输入/结果/草稿，不允许迟到复活；保留最小金融/幂等元数据不保留个人正文。页面 SHALL 披露 AI 处理/保存/删除，日志 MUST 不含个人正文、联系方式、Prompt、对象 key 或原始异常 payload。

#### Scenario: Foreign task operations
- **WHEN** 其他账号读取/编辑/导出/取消/删除/另存
- **THEN** 拒绝且不泄露内容或改变记录

#### Scenario: Source deletion races generation or save-as
- **WHEN** 源删与模型返回/导出/另存并发
- **THEN** 清理和状态屏障防止正文复活或创建未确认独立副本；未交付费用退还一次

#### Scenario: Processing disclosure and safe failure
- **WHEN** 创建或处理异常
- **THEN** 中文披露在确认前可见，错误只留固定状态/计数/时长且无用户正文

### Requirement: Additive migration preserving old wallet and runtime
迁移 SHALL 仅新建 CN optimizer 表及精确扩展既有不可变账本新 charge/refund 类型和 -100/+100 符号约束，不覆盖未知旧合法类型、不移除 trigger、不改写旧流水/会话/资料。旧应用 SHALL 与新 schema 兼容。源和接入 MUST 来自实际运行 CN Backend/Web 基线，保留完整原路由/schema、既有鉴权/状态读取/预取、普通/模拟/笔试/钱包/支付/助手清单。

#### Scenario: Repeat migration with an existing custom ledger kind
- **WHEN** 对带原合法扩展 kind 的本地基线应用/重复应用迁移
- **THEN** 原 kind 与符号限制仍合法且不可变，新两种类型仅允许正确金额，无破坏性 down

#### Scenario: Compare candidate to bound runtime
- **WHEN** 比较实际国服基线和候选
- **THEN** 旧完整路由/schema/保护方法及非目标配置保持，只包含批准功能增量

### Requirement: Unrelated public static content is preserved
新增功能 SHALL 沿用实际CN Web镜像中已发布的公开产品事实、搜索说明、功能文案和站点地图。恢复开发源码时 MUST 检查静态输入相对于实际部署文件的差异；与简历优化无关的公开内容不能混入本轮变更。本地完整dist MUST NOT 直接替换实际静态镜像中的旧资源、错误页或NGINX。

#### Scenario: Restored source contains unrelated public content drift
- **WHEN** 开发源码快照的5项公开输入与实际线上文件不同
- **THEN** 对齐线上原内容并保留前后SHA及失败/通过回归证据，构建后的对应5项也逐字相同，不发布任何线上变更

### Requirement: Existing mock interview remains accessible beside resume optimization
新增简历优化 SHALL 保留已启用的模拟面试导航、列表、历史报告和原流程路由。合成本地预览 MUST 显式模拟真实启用的模拟面试能力，不得以泛化的 disabled capabilities 响应隐藏原入口；真实服务关闭模拟面试时仍沿用原门禁。预览 SHALL 明确标注合成数据、无真实出题/收音，普通刷新后仍能恢复预览及两个入口，不调用生产服务。

#### Scenario: Navigate between resume optimization and mock interviews
- **WHEN** 已启用模拟面试的账号从简历优化工作台切换模拟面试并打开历史报告，再返回简历优化
- **THEN** 两个入口同时保留、各自正确页面可进入，普通面试/笔试入口保持，原关闭门禁仍有效

#### Scenario: Refresh the synthetic preview
- **WHEN** 用户刷新合成本地预览
- **THEN** 保留预览外壳并恢复合成配置，模拟面试与简历优化入口仍在且无生产网络调用

### Requirement: Synthetic local acceptance and deployment boundary
实现 SHALL 有专属中文 Prompt/evals，全部测试输入合成。自测 MUST 覆盖金融并发/跨日/失败/取消/重放、任务/权限/删除、中文事实正负例、编辑冲突/另存、真实导出渲染、中文页面状态及既有功能回归，并运行 typecheck/build/OpenSpec strict。交付 SHALL 准确区分本地自测与真实模型/生产长期指标。未经用户另行授权 MUST NOT 部署生产、提交推送 Git 或改国际服/助手/Admin。

#### Scenario: Local verification is delivered
- **WHEN** 本轮开发交付
- **THEN** 记录实际命令/结果/限制和逐场景证据，国服线上不变，不把合成结果称为真实模型或用户验收

#### Scenario: Future deployment is considered
- **WHEN** 用户后续明确授权上线
- **THEN** 重新检查实际镜像/配置漂移、只读活动门禁和固定回退后才发布，不终止用户面试制造空闲

### Requirement: Authorized CN production increment preserves existing services
用户 2026-10-18 已明确授权国服上线后，发布 SHALL 遵循 [生产追加规范](../../production-release.md)，以重新确认的 CN Backend/Web 实际运行镜像作为固定父基线，只实施已验收 20261018.2 功能增量和 CN 专属开关。历史本地交付记录 MUST 保留，未获授权的 Global/助手/Admin/Git 及原业务/收费调整 MUST NOT 混入。

#### Scenario: Authorized candidate is prepared and verified
- **WHEN** 为用户已批准的国服版本准备候选
- **THEN** 核对实际镜像/有效配置/全部旧源和完整路由/schema/原静态及 NGINX（只允许新页面路由 allowlist 字面量增量），绑定控制器和固定候选 SHA，实际隔离探针通过后才允许切换，不以旧目录或本地 dist 整包替代

#### Scenario: Protected work appears before cutover or recovery
- **WHEN** 迁移、任一组件切换或回退前存在活跃面试/收音/页面/任务/新优化工作，或门禁读失败/未知状态
- **THEN** 维持当前可验证状态并等待或报告，不终止用户、不修改记录制造空闲、不放宽保护；部分发布恢复时验证归属且不重复重启

#### Scenario: Production verification completes without real user generation
- **WHEN** 固定增量已完成切换
- **THEN** 独立核验实际镜像/配置、原行为和静态保留、公开健康和匿名私有鉴权，记录短时脱敏错误计数，真实模型/扣费/长期指标交由正常用户测试且不冒称已验收

### Requirement: Public candidate files remain readable by the actual NGINX worker
私有发布配置的0600策略 MUST NOT 用于公开静态产物。新Web公开文件及NGINX default.conf SHALL 为0644、公开目录0755，prepare SHALL 检查输入和实际候选镜像的模式。失败恢复后的重试 MUST 重新冻结实际容器与配置、使用新归属目录/标签，保留失败证据及additive schema，不对线上旧目录递归改权限。切换前 MUST 使用固定候选镜像运行隔离NGINX真实HTTP读取验证，不能仅依赖文件SHA、语法或本地Vite浏览器。

#### Scenario: Private staging permissions must not cause public HTTP failures
- **WHEN** 公开payload误为0600或实际NGINX工作进程无法读取候选入口/构建标识
- **THEN** prepare或切换前的隔离验证拒绝该候选；只有文件0644/目录0755且6个新旧应用/构建GET路径200与候选正文SHA一致后才允许重新preflight，私有配置仍0600，失败发布按既定门禁和归属保护恢复

### Requirement: Actionable privacy-safe failure reasons
国服 Provider SHALL 在首次失败位置产生固定allowlist原因，覆盖外层响应/结束标记/JSON/schema/依据/语言/改写事实/重叠/最终草稿；公共类别仍invalid_output。owner的既有errorMessage SHALL 通过固定中文映射区分可理解失败类别，未知/旧原因回退通用说明，不暴露内部payload或部分结果。原因、异常与日志 MUST 不包含用户正文、Prompt、响应、字段值、对象key或可识别标识；本轮仅本地合成修复，不自动发布或重跑真实任务。

#### Scenario: A user can distinguish a model validation failure
- **WHEN** owner读取新失败任务
- **THEN** 得到固定可理解中文原因及原退款提示，不误称上传/MinerU操作失败，原wire类别/权限保持；内部诊断字段不可见

#### Scenario: Untrusted content cannot enter diagnostics
- **WHEN** 合成响应含隐私哨兵并在任一解析/校验位置失败，或固定原因未知
- **THEN** 返回/异常/日志只含allowlist固定原因或通用回退，哨兵不泄露，跨账号请求仍拒绝；离线回归和AI eval记录准确本地验证边界

### Requirement: Authorized four-file CN Backend hotfix preserves the current runtime
用户后续明确授权的失败诊断热修复 SHALL 遵循[热修复生产规范](../../hotfix-production-release.md)，重新冻结实际995ae331…Backend父镜像、228完整输入、202完整路径/schema/有效配置和非目标状态，仅发布三既有文件及一个新增diagnostics。候选 MUST 通过实际禁网只读无生命周期/真实依赖副作用探针；DDL、环境、费用、Prompt、Web/NGINX、Global/助手/Admin/其它组件和Git MUST 不变，9.x本地历史保留。

#### Scenario: The four-file candidate is tied to the actual Backend
- **WHEN** 为已授权热修复准备候选
- **THEN** 实际源/归属/配置无漂移，229输入仅四文件增量，原202路径/schema和受保护行为相同，独立无副作用探针通过，不复用旧目录或本地测试代替候选证据

### Requirement: Hotfix cutover and rollback retain all seven protected-work gates
preflight、Backend切换及回退 MUST 在同一排他锁内重复完整七门禁，覆盖面试/页面/桌面/音轨/生成/Mock/资料及金融回调/CN优化工作。活动非零维持当前服务等待，未知/读取失败/过期样本/归属或配置漂移 MUST 停止自动切换并报告，不终止用户或清理记录制造空闲。回退 MUST 确认本次归属并使用固定旧镜像/原配置，不删除用户数据。

#### Scenario: A hotfix meets protected activity or unavailable gate
- **WHEN** 任一热修复切换或恢复前存在受保护活动或门禁不可信
- **THEN** 不执行该切换，不改用户状态/TTL；真实忙碌等待，未知或不可用停止自动切换报告，已有安全服务保持

#### Scenario: Owned Backend release is accepted or safely recovered
- **WHEN** 固定Backend热修复切换后核验，或候选失败需要恢复
- **THEN** 核对本次归属与实际镜像/完整源路由配置、原功能、非目标身份及公开/匿名私有鉴权；恢复前重读同七门禁，记录准确短时脱敏错误窗口，不称长期质量或原任务已成功

### Requirement: Mount signatures preserve the complete multiset
只有服务器只读证据确认Mounts前后完整多重集一致且摘要差异由排列导致时，发布工具 SHALL 可将Mounts最外层按每条完整canonical JSON排序后计算摘要/比较。全部字段/值/条目及重复数量 MUST 保留，嵌套数组顺序、HostConfig及其它保护保持；真实字段/条目变化 MUST 仍拒绝。修正 MUST 使用新目录/基线/控制器SHA/回归及实际候选验收，保留已停止尝试，不原地覆盖prepared证据。

#### Scenario: Only the Docker mount inspection order changes
- **WHEN** 服务器完整只读证据与合成回归确认同样Mounts条目仅最外层排列不同
- **THEN** 全字段稳定规范化得到相同摘要，无挂载修改操作；新修正候选需重新冻结和验证，原停止证据保留

#### Scenario: A mount field or multiplicity actually changes
- **WHEN** 已知或未知字段/值、条目增加删除或重复数量变化
- **THEN** 完整规范化仍产生差异并停止切换，不忽略挂载保护或覆盖旧基线，未获归属/活动门禁通过不恢复或重启

### Requirement: Authorized 11x development stays local and protects the live baseline
用户已明确要求11.x优化开发，本轮 SHALL 本地实现/自测/预览，root明确strict实施GO前不改业务；暂不执行生产切换/Git/Global/助手/Admin或费用/DDL/环境变更。实际6f2a…Backend229源/202路径/340Settings及20d6…Web305静态/NGINX已只读重新绑定，旧功能和claim/source/cancel/账本保持。实际compiled本地候选 SHALL 最小增量保留全部旧hash/正文/CSS/NGINX/普通模拟笔试，不能全dist覆盖；后续上线另需当时实际镜像、完整七门禁和固定归属恢复。

#### Scenario: Local development preserves the frozen live product
- **WHEN** root明确GO后开发并进行本地真实PG/API/Browser自测
- **THEN** 安全partial成功/零有效失败退款、原权限/竞态/计费及既有导航/静态均有新回归和可审查预览，不生产切换或用真实用户数据作夹具

### Requirement: Three synthetic Provider QA cases remain bounded and isolated
明确GO后的真实Provider QA SHALL 最多3个固定约3千字符技术合成用例各一次，仅服务器私有配置/候选隔离进程/原预算；候选先禁网只读无生命周期探针，每次前完整七门禁并先消费候选/Prompt/script/case绑定marker。只留固定安全结果/计数/时长及合规实际修改判据，不读取用户资料/OSS/任务、不创建job/usage/账本/面试、不碰钱包；失败停止，不自动重试/追加。合成通过不代表用户原任务已成功或生产上线。

#### Scenario: Three synthetic provider cases remain bounded and isolated
- **WHEN** GO后用明确可改善的合成技术内容验证真实模型与partial/summary合同
- **THEN** 每例最多1请求、门禁/marker完整、实际合规局部修改和计数通过；空或全无效须失败退款语义而非假成功，不用户任务重放或生产业务写入

### Requirement: Pre-start QA tool failures do not become model retries
若实际Docker/runc挂载失败且安全证据明确证明容器进程未启动、Provider请求0，QA工具 SHALL 保留原consumed marker/控制器/prepared/失败记录并停止后例；只有QA工具修正与实际Linux Docker禁网只读演练、完整新目录/plan/controller/tag重冻及root独立GO后，才可恢复原三例各一次的计划。本轮总实际Provider请求 MUST 仍<=3。若Python/请求可能已开始或状态未知 MUST 停止，不清旧marker、不换目录重试模型或放宽产品验证。

#### Scenario: A proven pre-start mount failure keeps the consumed attempt
- **WHEN** 安全分类确认首轮case1只在runc容器init的挂载创建阶段失败，进程未启动且Provider请求0
- **THEN** 保留dir1失败和consumed marker、不开始后例，11.6/C73仍未完成；只允许root重审后的独立dir2工具修复，不声称模型或生产已通过

#### Scenario: A synthetic case uses one verified read-only directory mount
- **WHEN** 新QA目录恢复原计划前准备当前合成case
- **THEN** 在QA排他锁内先写真实存在的case.json为0600并核对冻结SHA，容器仅一个整个QA目录的只读挂载；实际Linux Docker禁网演练通过，随后仍须candidate/七门禁/持久单次marker和安全输出验证，不嵌套挂不存在目标或接触业务数据

### Requirement: Authorized safe-edit production release refreezes actual CN targets
用户最新明确授权的12.x生产发布 SHALL 遵循[安全局部改写生产规范](../../safe-edit-production-release.md)，以重新确认的实际CN Backend/Web父镜像及完整源/schema/Settings/静态/配置/归属为基线，仅发布已验收Backend3源和Web15patch。原229→230输入/202完整schema/340Settings、305旧路径→315及全部非目标 MUST 保持批准的最小差异。相对已验收本地315候选，唯一新增差异 SHALL 是build元数据appVersion由.local改为正式cn-resume-optimizer-safe-edits-20261018.1，其余14patch及JS hash不变、不重编译；CSS/NGINX/全部旧hash资产及4HTML公开正文保持。无DDL/有效环境/费用/依赖/额外模型/Git或Global/助手/Admin变化。

#### Scenario: Refreeze actual CN components before safe-edit release
- **WHEN** 用户已授权12.x上线而root准备实施
- **THEN** root独立strict GO及实际完整镜像/源路由schema/Settings/静态配置与非目标签名匹配后才实施生产工具，不用旧目录/健康版本/本地候选替代实际来源；漂移停止报告

#### Scenario: Safe-edit candidates pass isolated backend and NGINX probes
- **WHEN** 固定生产候选已按三源/十五正式patch准备
- **THEN** Backend实际禁网只读无生命周期230输入/202schema/340Settings/七副作用0及safe partial/零有效/真实导出合成探针通过；Web315保留/正式build唯一差异，按实际旧20d6模式SHA精确继承8固定原元数据0755、其余原文件/15新patch/NGINX0644、10目录0755，nginx用户全部316可读且隔离真实NGINX读取HTTP/SHA通过，不向生产账号或模型发测试
- **AND** 精确名单/基线SHA按生产规范第7节绑定，未知/多缺路径/正文0755/新patch非0644/目录非0755或不可读均拒绝；dir1停止证据保持，新dir2复用固定Web2124eee8…重新全部探针，不chmod旧资产或通用接受644/755

### Requirement: Safe-edit cutover and recovery protect all live work
12.x preflight、每个Backend/Web实际切换与回退 MUST 在同一发布排他锁内重复完整七门禁，保护全部原面试/页面/桌面/音轨/生成/Mock/资料/金融/CN优化工作；完整Mounts多重集和所有非目标配置/归属保护保持。有效busy SHALL 保留当前安全状态等待，unknown/readfail/非法/过期/漂移 MUST 停止并报告，不终止用户/清理活动/改TTL制造空闲。固定Backend→Web切换，部分状态核归属且不重复重启；失败只在同样门禁空闲和本次归属确认后Web→Backend固定回退。仅IP实际变化允许既有Web/Admin nginx -t后必要DNS reload，不改配置/镜像/启动身份或重建非目标。

#### Scenario: Protected work defers every safe-edit switch or recovery
- **WHEN** 任一12.x切换/恢复门禁发现真实活动，或unknown/readfail/非法/过期/漂移
- **THEN** 有效活动维持当前服务等待，其余停止自动动作并报告，全部保护字段保持，不结束面试/优化或删除任务制造空闲

#### Scenario: Ordered safe-edit cutover resumes without duplicate restarts
- **WHEN** Backend已按固定候选更新而Web前出现新活动，或本次发布已有已部署标记
- **THEN** 保留可验证部分状态，恢复先核实际归属/结果并跳过已完成组件；空闲时才继续固定Web，不重复重启或扩大非目标变化

#### Scenario: Owned safe-edit rollback preserves users and data
- **WHEN** 实际切换/验收失败需要恢复
- **THEN** 先确认本次归属并重复七门禁，空闲才按Web→Backend恢复固定旧镜像/配置；新活动或未知漂移停止报告，任务/资料/账本/新结果和所有历史失败/QA marker保持，不删数据或撤销消费

### Requirement: Safe-edit release acceptance separates actual deployment from local quality
12.x完成 SHALL 由独立verify和短时脱敏观察证明实际两目标镜像/归属、230源/202schema/340Settings/315静态/有效配置及原功能/非目标保持，公共GET及匿名401/private,no-store正确。仅输出固定错误/计数/覆盖秒数，不能导出原日志/用户标识或声称长期P95/所有简历成功。生产验收 MUST 不调用额外真实模型、不创建生产测试job/费用/资料/面试，保留47任务/75场景本地验收及旧发布/QA失败历史。

#### Scenario: Independent safe-edit acceptance reports actual deployment scope
- **WHEN** 固定Backend/Web切换和独立验收实际结束
- **THEN** 依据真实镜像/来源/路由配置静态/权限HTTP及实际覆盖短窗记录12任务与生产结果，再通知用户正常测试；未完成或受保护部分状态准确披露，不把本地QA当上线或长期质量
