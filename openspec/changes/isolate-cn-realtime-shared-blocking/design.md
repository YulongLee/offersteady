## Context

用户已确认在不改变现有体验的前提下本地优化、自测，晚上另行发布。当前CN Backend为5efba4ab…，完整233输入见docs/releases/cn-device-status-20261103.1/backend-runtime-manifest.json；前轮隔离候选candidate-final与该清单全部相同。根目录保留前轮已部署但未提交代码和未发布笔试配套，不能整仓覆盖线上。

历史峰的唯一阻塞调用占比尚未测得；健康检查及模型请求标记前的等待证明共享调度延迟。纯合成已复现同步ASR close阻塞主循环、候选快照持锁跨Redis写阻塞其它会话。批量读取将同次逐文档statement变为一次statement权威快照，不声称并发采点完全相同。

## Goals / Non-Goals

**Goals:** CN实时同步I/O与慢关闭隔离；逐连接保序和资源拥有权正确；实体持久化去除全局快照写放大；单次资料批读；数值观测；实际基线构造与业务回归。

**Non-Goals:** 不部署、SSH、提交/推送，不改Web/助手/Global/worker/模型/Prompt/收费/收音协议/轮询频率/连接池/SQL迁移/依赖，不进行真实模型或用户数据测试，不引入ANN或承诺线上P95固定降幅。

## Decisions

### 1. CN执行隔离与取消收尾

新增独立有界执行器，ingress默认4 worker/16排队槽，lifecycle默认2/8；原control、answer和event-wait资源不变。CN publisher准备/创建、WS连接/引导/帧准备/断开与兼容入口同步工作按原顺序await；不为每帧起无界线程，不并发重排同一连接。慢关闭不进入短控制lane。Global及mock独立legacy分支保持原合同。

同样会同步关闭ASR的CN capture-control暂停/恢复纳入lifecycle；实际service用现有引用计数session cleanup锁串行化pause/resume/end，在锁内读当前权威状态，避免移到线程后恢复与结束乱序。原收费、停止与错误body保持，Global仍直接沿原body。其它非目标只读/确认入口不在本轮声称全部治理范围内。

调用图核查发现session的end和supersede两个async入口也直接执行上述终止/cleanup锁/close；这两个CN入口的原校验、终止及最终读取整体交lifecycle，保留expected_previous、模式及错误合同；Global原路径，start/restart及其它session实现不扩展。

正常CN lifespan注入执行器；无lifespan测试/原型沿兼容to_thread fallback，但同样shield/drain。取消尚未提交工作可退出；已提交工作不重放，先完成或确认取消再清理。slot在真实worker完成时释放。成功但调用者取消的publisher创建/连接须恰好一次补偿disconnect，重复cancel继续等待同一工作。shutdown停止接纳、取消排队并wait=False关闭，不能硬杀已运行Python线程或许诺未知外部I/O可被强制终止。

替代方案：所有工作放默认线程池会把长close传播到其它同步API；裸to_thread取消会留下晚到publisher；每帧并行会改变sequence/terminal语义，均不采用。

### 2. CN实体原子持久化

只对CN启用候选按session实体及索引、账号设备关联实体与既有绑定实体的原子写，网络I/O不持进程全局runtime锁；短内存更新仍受锁保护。使用Redis原子操作维护owner、版本/时间单调、索引及活动版本，失败不得假报保存或重放业务。冷启动兼容旧snapshot，只在新实体缺失且未退役时seed，不能覆盖新值；读路径优先权威实体，删除/缺失处理不从旧内存复活。

clear在删除前原子建立session退役fence，清候选及原临时状态；保留原stale binding返回及账号历史。tombstone/seed marker期限覆盖旧snapshot剩余寿命与当前runtime；旧snapshot不续期，不删除旧key。原restart创建新sessionId，continue不复活ended；未clear的合法同ID重绑保持。测多实例新代码并发、seed/clear竞态和过期恢复。

兼容是新代码读取旧snapshot及保留旧key，并非允许未修改旧binary并行写。后续生产发布必须确认单Backend writer、无活跃用户并固定回退；旧binary无法读取仅新实体的活跃变更，因此禁止在活跃面试期间回退或混跑。直接去锁或在锁外整包写会失序覆盖，不采用。

新CN绑定的canonical及两个索引使用独立命名空间，不能把新envelope写入旧v1绑定key；旧值仅作兼容seed并保持可由旧代码解码。绑定退役状态原子持久化，数组/数值原JSON保持；所有可能续实体寿命的活动也续保护/索引期限，避免保护先过期或索引过期后反复全扫。

候选没有独立revision且可能同毫秒更新；CN领取/绑定/释放等依赖旧值的转换使用可选compare-and-save原子入口，以原record/版本作为期待值，冲突不能覆盖、重放领取或重复发起回答。无该能力的既有仓库与Global沿原路径。必要服务适配只限候选转换，不覆盖前轮设备状态方法。

### 3. 一次操作内资料批读

Postgres文档仓库提供可选内部get_by_ids，同列/同JOIN用ANY一次statement；不增加强制抽象方法。CN非mock get_session在进入原刷新算法前预填本次原始记录，包含缺失None；不改list_sessions已有seed复用和Global/mock选定版本行为。RAG metadata按唯一文档批读，逐候选按原顺序进行owner/status/version/kind/collection过滤和排序。无批读能力的实现逐唯一ID fallback，下一调用重新读取。预取前后两个get_session及最终指纹验证保留；无需修改chat算法。

替代方案：跨请求缓存权限/资料会过期；直接取消预取后检查会提交旧结果；强制所有仓库实现新抽象扩大兼容面，均不采用。

### 4. 有界数值观测

CN lifespan运行低频主循环延迟探针，固定上限样本和数值摘要；工作按固定低比例采样，operation/lane为白名单，区分入场/排队、worker执行与loop恢复。只增加私有数值日志/既有metrics字典，不新增UI说明或HTTP路由。计时/日志失败不改变业务；不记录ID、SQL、URL、payload、资料、异常文本，不把工作相位简单相加或称为纯模型耗时。

### 5. 当前实际基线及验证

冻结233输入为独立baseline；仅允许本轮必要源增量构造candidate，未改输入逐SHA一致。203条完整OpenAPI、344有效Settings及助手d7清单、Prompt、模型、依赖、旧笔试路由保持。测试使用合成仓库和localhost专用Redis/PostgreSQL，不读取产品.env或生产数据；真实协议/取消/清理并发场景与慢I/O对照是验收重点，不能把本地结果换算整体生产P95。

233份为此前捕获的核验输入，并非镜像所有层的完整清单。Dockerfile单独复制的material-upload-formats.json不在其中；本地上传回归仅通过test-only路径解析读取任务开始前SHA相同的本地辅助文件，不修改冻结候选。未来实际镜像探针必须验证该保留文件，不能把本地来源当生产来源证明。

## Risks / Trade-offs

- [后台晚到资源/槽位提前释放] → shield/drain、worker完成释放及幂等补偿测试。
- [实体迁移丢恢复/复活ended] → 旧snapshot seed与实体/退役原子优先、TTL及多实例竞态测试；禁旧writer混跑。
- [批读改变并发观测点] → 明确单statement快照、每次独立重读和末尾指纹复核；保留错误/删除/权限。
- [本地混入未发布输入] → 固定233实际输入与允许列表构造、非目标hash和完整schema验证。
- [优化后仍有其它瓶颈] → 明确工作范围和计时边界，后续正常流量对照，不承诺根治所有尾延迟。

## Migration Plan

本轮仅本地候选与报告。晚上另获发布指令后，重新核对目标实际镜像、完整输入和私有配置，冻结兼容回退，确认无旧writer和所有用户工作门禁空闲后才准备/切换；不将本地测试当成部署授权。

## Open Questions

无阻塞产品选择。真实高峰各阻塞点的占比、未来索引/池的收益须新分段及同负载验证。

## 2026-11-04 生产追加方案

### 授权、增量与实际基线

用户已明确授权国服发布，本节取代此前仅本地阶段对SSH和部署的限制，其它非目标不变。起点记录为实际Backend镜像`sha256:5efba4abea9b12e1af2b9d2c6e8f6edb2c205afed93f4f9fc9ba862e96499229`及[233输入清单](../../../docs/releases/cn-device-status-20261103.1/backend-runtime-manifest.json)，清单SHA为`18d50582a66b4bb338301ea405ee650347c41a8998391732eab2b99ea6ba224b`；发布前必须重新核对实际容器Id、固定镜像、StartedAt、完整已捕获输入与私有配置，不能将此记录当成新鲜核对。

仅允许[冻结清单](../../../docs/releases/cn-realtime-shared-local-20261103.1/delta-manifest.json)的十二个运行文件：`app/main.py`、`app/modules/realtime_speech.py`、`app/modules/session.py`、`app/services/realtime_speech_service.py`、`app/services/redis_realtime_speech_repository.py`、`app/services/cn_realtime_entity_state.py`、`app/services/cn_realtime_io_executor.py`、`app/services/session_service.py`、`app/services/knowledge_retrieval.py`、`app/services/postgres_material_persistence.py`、`app/platform/cn_realtime_lifespan.py`和`app/platform/cn_realtime_loop_monitor.py`，均相对`apps/backend/`。预期八个既有文件修改、四个新增，233→237份捕获输入，225份非目标字节和权限保持。未发布笔试配套等根目录其它修改不得进入候选。

从实际固定镜像保留原Config及基础层前缀，仅COPY十二文件构造固定候选，不全量构建或安装依赖。固定原镜像为兼容回退并核实其实际d7下载清单；不得使用撤销已发布优化或助手清单的更旧镜像。prepare冻结Compose/env/rendered私有快照、来源与配置指纹、控制器/探针/support及镜像SHA，私有内容只留服务器。实际候选镜像用network-none、只读和资源受限的合成探针验证，不启动应用lifespan，不接生产DB/Redis/模型；验证237输入/225保持、完整203Schema、344有效Settings、44依赖/Python及助手d7清单。单独复制且不在233中的`material-upload-formats.json`必须从实际镜像核对，不用本地辅助文件冒充生产来源。

### 空闲门禁和单writer切换

prepare/preflight、最终停旧容器前以及任何失败恢复前，重复原七项只读用户工作门禁、新增第八项`cn_entity_idle_gate`及当前Backend TCP8000门禁，并证明本轮CN运行态仅有目标Backend writer。第八项是独立附加门禁，不替代或放宽原七项：只读检查新CN namespace中的binding、candidate、CAS claim及退役、owner、activity元数据，避免旧snapshot检查漏掉新实体中的保护工作，尤其不能在回退时遗漏。不得构造会seed的业务仓库、续TTL、清key或改变claim；未知格式、读取失败、归属/活动元数据无法解释均fail closed。仅存历史退役/owner记录不能直接当作活跃工作，其分类与完整性须由冻结探针及合成回归证明。

普通/笔试/模拟会话与准备页、音轨/桌面发布者、未完成回答/截图、资料/简历任务和有效账务均受保护。财务历史下界仍固定`1792600214792`，与新鲜实际baseline Id/StartedAt的orphanAnswerContext分离，不能因本次重启重新分类历史记录。不得结束面试、清活动、放宽阈值或增加准备页例外。只有`protected_user_work_cutover_deferred`是正常等待；unknown、读取失败、任何漂移均停止并报告。

preflight空闲不替代最终检查；后续有用户工作进入即延期。全部门禁通过后先停止已证明归属的旧Backend，再启动唯一固定候选，不能滚动混跑旧snapshot writer与新entity writer；七个非目标容器、Web、助手、Global和worker保持。新CN绑定使用独立namespace，旧snapshot及v1绑定字节只作兼容seed而不被新envelope覆盖；不得通过清空Redis或续写旧snapshot来制造兼容。

### 归属恢复及新旧状态边界

旧binary不能读取只写入新entity的活跃变更，保留旧key并不等于活跃回退兼容。候选失败时先证明本次发布归属、冻结输入/配置和single-writer状态，再重新运行原七项、新增CN实体门禁和TCP门禁；只有全部再次空闲才可停止候选、恢复固定原镜像并核验。候选已接纳用户工作时必须等待，不能因健康失败而中断用户或自动切回旧binary。未知归属、漂移、读取失败或恢复失败均停止并报告所需处置。

若原容器仅停止而候选尚未创建，只能在重新空闲门禁和双重原Id/Config/Stopped核对后启动该原容器；不恢复外来进程。已部署重入仅核对归属和真实结果，不重复重启。任何切换路径都不得同时运行旧新CN writer；不声称尚未修改的旧binary可看到新entity更新。

### 真实验收与发布记录

切换后核对候选固定镜像、237输入及225份非目标、原私有配置、完整Schema/依赖/Python、上传格式及d7清单、健康/重启、原公开路由与Web公开文件，以及七个非目标容器签名；另跑独立verify和短时服务器侧ERROR/CRITICAL/traceback/HTTP5xx脱敏聚合，并记录新队列/主循环数值观测。真实异常必须如实保留，不因短窗口没有错误承诺长期无问题。

生产数据仅用于必要只读门禁与汇总，不导出原始日志、凭据、会话标识、材料、音频或个人资料；不创建真实面试/付款、不调真实模型、不生产压测。不改Web/助手/国际服/worker、模型/Prompt/收费、SQL结构/索引、依赖或连接池开关，不提交/推送Git。保存脱敏证据、更新生产发布记录及本节任务状态，完成后通知用户测试。本地合成956通过/1跳过与短时线上验证均不能换算整体生产P95。

### 2026-11-04 用户追加授权：仅原Backend最多一条残留TCP

用户后续明确要求继续上线，并接受当前原Backend的一条残留连接随正常更新断开。此项仅覆盖此前因该残留TCP而等待的条件，不覆盖任何面试、准备页、发布者、回答、任务或账务门禁。新增冻结目录`20261104-cn-realtime-shared-3`承载明确例外，保留`-2`不覆盖，旧自动等待已删除。

TCP8000的默认零连接规则只有同时满足以下全部条件时可接受0或1：尚未发生本次切换、当前操作不是recovery/rollback，运行容器精确Id为`035642d58f7eb9ad16f46a830d153130b1d2d6e7851401b0ec620cdaeed101bf`且镜像精确为`sha256:5efba4abea9b12e1af2b9d2c6e8f6edb2c205afed93f4f9fc9ba862e96499229`，原七项与新增CN实体门禁保护工作全零，读取结果、owner、单writer、来源及冻结材料全部验证通过。prepare/preflight与最终停旧容器前均重新验证这些条件；不将之前的结果复用为例外证明。

TCP大于1、出现新保护工作、unknown、读取失败、归属或来源不符仍阻止部署。新候选、已切换后的任何过程、其它容器以及所有恢复/回退仍必须TCP为0，不继承原服务的例外；恢复原容器也属于recovery，不能使用此例外。不得先单独断连、结束用户、清状态、改账务或放宽八项用户工作门禁；仅由正常固定Backend更新使允许的一条残留连接断开、客户端重连。

## 2026-11-04 第7节本地修复方案：CN pinned绑定定点查询

### 来源、边界和现存问题

第6节发布已完成，本节不修改其历史结果，也不追加生产操作。新起点是实际dc8固定镜像及其[237输入](../../../docs/releases/cn-realtime-shared-20261104.1/backend-runtime-manifest.json)，按最终必要文件清单构造本地最小增量，保留其余运行输入、完整API/配置/依赖、d7助手清单和辅助上传格式文件；不把旧5ef目录或根目录完整源码当成现行基线。

配对状态查询的pin分支当前调用`list_session_desktop_bindings_for_device`后筛选session/binding；CN实现通过`all_records("binding")`执行全站`HVALS`并对每个记录检查退役状态。即使只有一个当前测试用户，读取工作量仍受保留的全站历史影响。本地修复仅替换这一单个pinned查找，不取消原鉴权、会话检查、状态分支、缓存generation失效规则或latest fallback，不顺手重构所有列表/后台指标。

### 可选方法与原子定点读取

服务在CN带完整pin参数时优先探测仓库的新可选内部方法；无此方法的已有仓库继续原列表匹配路径，Global与mocks保持原实现。无需增加强制抽象方法或HTTP/助手协议字段。

新CN仓库方法沿现存session→owner索引，读取该owner/session对应的canonical绑定及retired fence；以单次原子只读操作形成一致的绑定、owner和退役观察点。有效pin查找不执行`HVALS`/全站扫描，不批量解码无关绑定，不修改TTL、索引或业务状态，不增加跨请求缓存。必要的session/owner索引缺失或不一致不得凭旧进程内存猜测归属，按pin未命中或原错误合同处理。

定点方法/服务组合仍校验请求manualCode、注册deviceId、pinnedSessionId、pinnedBindingId与返回记录一致；保留generation、新鲜度、bound/stale及retired含义，并继续原`get_control_state`数据库权威会话检查。pin不存在、参数不完整、记录不匹配或已失效时，保持原`bindingLockState`释放及`get_latest_session_desktop_binding_by_code`回退顺序/错误合同，不静默把无效pin报告为held。latest索引缺失时的既有修复行为不纳入本次定点命中恒定工作量承诺。

### 竞争与验证

用可控屏障覆盖读取与retire、DB end及rebind/generation变化的交错。原子读取先观察到退役/替换，或权威会话检查先观察到ended时，旧pin不得成为held/可用；合法新绑定及原latest fallback仍可用，原缓存generation失效规则保持。并发结果须能按原子读取与权威会话校验的顺序解释，不声称能够预知已返回后才发生的终止，也不新增缓存来掩盖竞争。

先用当前dc8等价来源构造失败回归，再实现最小修复。1、1191和10000条绑定规模均使用合成记录，固定有效pin和其索引，只增加无关历史；分别证明Redis查询/解码数量与历史总量无关且不调用全站`HVALS`，同时记录本地耗时而不换算线上P95。混合轮询需包含带pin配对、普通配对及现有控制读取，避免只测孤立helper；安全回归覆盖错误owner/code/device/binding/generation、retired/missing/ended、重绑与pin失效latest回退，以及无新方法仓库、Global/mocks和旧助手请求合同。

只在本地运行必要回归及独立审查，冻结实际来源和最终允许diff，逐文件复核非目标保持并保存脱敏证据。没有SSH/上线、真实模型/面试/付款、生产压测或Git操作；不改Web/助手/国际服/worker、收费、模型/Prompt、连接池、SQL结构/索引、依赖或生产配置。后续上线须重新授权及核对当时实际组件，不能重放第6节控制器。

## 2026-11-04 第8节三文件修复生产追加

按用户最新指令将第7节候选部署国服。以新鲜只读核对的dc8/7849及237输入为基线，固定原dc8作为兼容回退；从实际镜像只COPY三份已冻结修复文件，Config/基础层、234份非目标、辅助上传格式、d7清单与其它组件保持。新目录`/opt/offersteady/releases/20261104-cn-pinned-binding-1`与新控制器`release_cn_pinned_binding.py`独立冻结，不复用旧发布的启动状态或残留TCP授权。

复用已审查的冻结Compose、归属/漂移检查、原七项门禁与第八项CN实体门禁及single writer；新控制器无TCP例外，切换与恢复均TCP8000为0。最终切换重新读门禁；新旧writer不能混跑。未知、读取失败、源码/配置漂移或恢复失败停止并报告，不因急于修复而中断用户。等待期间可准备固定候选，不能清活动或断连。

实际候选镜像以network-none、read-only及服务器本地私有环境运行合成探针：全部237输入、203完整Schema、344有效配置、44依赖、Python、上传格式及d7保持；保留上一轮调度/取消/资料/模式探针，增加新getter及服务分支的常数查询、身份/退休/精度/兼容验证。真实Redis Lua及1191/10000历史规模的执行证据来自已完成的本地独占Redis测试，实际镜像离线探针的模拟必须明确边界，不冒充接入生产Redis验证。

发布后独立verify实际镜像、237/234、私有配置及非目标，短时脱敏聚合ERROR/traceback/5xx和自然active-connection请求分布，明确重启窗口与5分钟旧样本的影响。没有自然有效pin请求时只交来源/健康验收，不补造收益；不制造用户请求/模型/压测。完成生产记录、实际基线和任务后通知用户测试。私有配置及原始日志/标识留服务器，不提交推送Git。
