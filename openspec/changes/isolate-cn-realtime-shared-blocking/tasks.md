## 1. Scope and frozen baseline

- [x] 1.1 冻结当前实际233输入及本轮前工作树，核对允许范围、OpenSpec apply-ready和用户本地授权。

## 2. CN scheduling isolation

- [x] 2.1 实现独立有界ingress/lifecycle执行器、数值采样及取消/drain/资源补偿。
- [x] 2.2 接入CN publisher、新旧WS/frames、capture暂停恢复及session end/supersede同步关闭入口，保持Global/mock及协议/权限/顺序，串行同会话pause/resume/end。
- [x] 2.3 接入CN生命周期与有界主循环延迟观测，确保关闭/观测失败隔离。
- [x] 2.4 验证慢关闭/Redis、容量、取消/重复取消、晚到创建/帧、断开替换与非目标路径。

## 3. CN runtime persistence

- [x] 3.1 实体化候选/关联/绑定并原子维护owner/版本/索引/活动状态，消除全局锁跨网络写。
- [x] 3.2 兼容旧snapshot安全seed、退役fence及TTL，保留stale binding、账号历史和重启/clear幂等。
- [x] 3.3 回归多实例、同毫秒竞争、seed/clear/晚到写、恢复/过期及跨会话慢Redis隔离。

## 4. CN operation-local document reads

- [x] 4.1 实现可选文档批读及CN非mock get_session本次预填，保留list/Global/mock与fallback。
- [x] 4.2 实现CN检索metadata同次批量去重，保留候选过滤/排序和前后资料指纹检查。
- [x] 4.3 验证批读减少、缺失/异常不重试、跨请求更新/删除/版本/权限和原业务等价。

## 5. Candidate verification and handoff

- [x] 5.1 从实际233基线按允许列表构造独立candidate，核对完整203 Schema、344配置/依赖/Prompt/助手清单及非目标SHA。
- [x] 5.2 执行隔离Redis/PostgreSQL、混合并发/慢I/O与普通/笔试/模拟/计费/鉴权相关回归，记录实际通过与限制。
- [x] 5.3 独立审查并修复本轮问题，复核全部Spec场景、strict、文档链接与diff检查，交付本地报告；不部署/提交/推送。

最终结果：冻结候选956通过、1项Global专属跳过；16个能力场景逐项核对、237输入SHA及225份非目标权限保持。独立审查、strict和Markdown链接/diff检查通过。详见[本地自测报告](../../../docs/releases/cn-realtime-shared-local-20261103.1.md)。未部署或提交/推送Git。

## 6. Authorized CN Backend production release — 2026-11-04

用户已授权国服发布；上文“未部署”是本地交付时的历史事实，后续生产结果逐项记录，不提交/推送Git。

2026-11-04追加：用户明确接受仅精确原Backend的最多一条残留TCP随正常更新断开。按生产spec的精确Id/image、尚未切换、非recovery、原七项+CN实体保护工作全零及全部读取/owner/来源证明条件，仅原服务TCP可为0或1；其它情况与任何恢复/新候选仍TCP为0。新冻结目录`20261104-cn-realtime-shared-3`，不覆盖`-2`，旧自动等待已删除；不单独断连或清状态。

- [x] 6.1 补齐生产追加proposal/design/spec及本节任务，核对用户已授权范围，通过strict和文档链接检查。
- [x] 6.2 只读重新核对实际Backend Id/固定镜像/StartedAt、233捕获输入、额外上传格式文件、344有效配置/44依赖/203完整Schema、d7助手清单与七个非目标签名；冻结私有配置、控制器/探针/support及固定候选/原镜像回退，漂移则停止。
- [x] 6.3 从实际固定镜像仅叠加十二文件，运行隔离实际镜像合成探针，核对237输入/225保持及基底层/Config/有效配置/完整Schema/依赖/上传格式/助手等价，不启动lifespan或接生产DB/模型。
- [x] 6.4 在prepare/preflight及最终切换前重复原七项只读用户工作、新增第八项cn_entity_idle_gate、TCP8000及单CN writer门禁；第八项独立只读覆盖新namespace binding/candidate/CAS claim及退役/owner/activity，不替代或放宽原七项，unknown fail closed；仅按追加授权允许精确原Id/image、尚未切换且非recovery、八项保护工作全零及所有证明成功时TCP0或1，>1/新工作/unknown/读取失败仍阻止；保持财务下界与新鲜orphanAnswerContext分离，不结束用户。
- [x] 6.5 用户工作全零且所有证明/TCP适用条件通过后，仅正常停止已证明归属的旧Backend并启动固定候选，不单独断连/清状态，禁止旧新writer混跑；失败恢复重新通过原七项+CN实体+严格TCP0+单writer及归属门禁，不继承原服务残留连接例外，保护新实体中尚在进行的工作，已接纳用户工作不得回退，已部署重入仅验收。
- [x] 6.6 完成独立verify、实际镜像/237输入/225保持、配置/完整Schema/依赖/健康/原公开路由/助手/Web及七非目标复核，采集短时脱敏ERROR/CRITICAL/traceback/HTTP5xx与新增数值观测，明确真实异常及P95观测限制。
- [x] 6.7 保存脱敏证据，更新生产发布记录及任务实际结果，通知用户测试；确认无真实模型/面试/付款/生产压测，无其它组件/收费/模型/池/结构变更或Git提交推送。

生产结果：2026-11-04 03:33:48（北京时间）发布与独立verify成功，固定dc8镜像/7849容器，健康且RestartCount0。237输入/225保持、203完整Schema/344配置/44依赖、辅助上传格式/d7助手、366Web及七非目标通过；独立复核无阻塞发现。17次实时控制502限于启动后0.571–3.571秒，验收后及补充最近60秒为0。短窗主循环调度观测不代表API P95改善。自动等待任务已删除，无Git提交/推送；[完整发布记录与脱敏证据](../../../docs/releases/cn-realtime-shared-20261104.1.md)。

## 7. Local CN pinned-binding lookup repair — 2026-11-04

用户已要求优化并避免回退；本节仅本地开发、自测与审查，不修改第6节已完成生产历史，也不复用其发布授权。不SSH、不上线/重启、不调用真实模型/面试/付款、不生产压测、不提交推送Git；只CN Backend，不改其它组件、助手协议、收费、模型、池、SQL结构/索引、依赖或私有配置。

- [x] 7.1 以实际dc8固定镜像及237输入冻结本地来源、任务开始前工作树与允许范围，核对已发布功能/API/配置/依赖/辅助上传格式/d7清单；候选仅叠加最终必要最小diff，不从旧目录或根目录完整构建，不预锁文件数量。
- [x] 7.2 先补可复现有效pin分支全站读取的失败回归；用1/1191/10000条合成绑定证明当前工作量增长，明确现有结果及计时边界，不读取生产用户资料。
- [x] 7.3 仅为CN完整pin读取增加可选仓库定点方法，沿session→owner索引原子只读canonical绑定/退役状态；保留全部身份/generation/DB权威会话检查、失效pin原latest fallback、旧仓库原路径及Global/mocks/旧助手合同，不增加缓存或改写状态。
- [x] 7.4 验证1/1191/10000历史规模下有效pin查询/解码次数固定且全站HVALS为零，运行带pin配对/普通配对/控制读取的混合轮询及必要后端回归，记录实际本地耗时、差异与限制，不换算线上P95。
- [x] 7.5 回归owner/code/device/session/binding/generation错误、retired/missing/ended、retire/end/rebind交错、cache generation失效、合法新绑定与latest回退、旧仓库fallback、Global/mocks及普通/笔试/模拟和旧助手兼容，核对非目标输入保持。
- [x] 7.6 完成独立审查、Spec场景逐项核对、strict及链接/diff检查，保存实际来源/最小diff/规模与安全回归的脱敏证据并交付本地结果；后续部署另候用户指令，不重放旧生产控制器。

第7节本地结果：三文件增量、237输入/234非目标字节权限保持；红测试复现1/1191/10000历史下全量读取，修复后三规模均3次Redis往返/1次绑定解码/1次权威会话读取，服务端全站扫描增量0。12助手/1live混合回归通过；冻结候选986通过/1项已知Global专属跳过，另2项屏障交错用例通过。独立审查无阻塞；[本地交付与证据](../../../docs/releases/cn-pinned-binding-local-20261104.1.md)。本轮未SSH、上线或提交推送Git，生产仍为dc8，需后续另行发布。

## 8. Authorized CN pinned-binding production release — 2026-11-04

用户已授权部署第7节三文件修复；仅本节可执行必要生产操作，严格TCP0，不继承旧发布残留连接例外，不重放旧控制器。

- [x] 8.1 追加生产范围/方案/Spec与任务，通过strict，冻结dc8实际组件新鲜观察与237输入/辅助上传格式/有效配置/Schema/依赖/d7/Web/非目标及控制器来源。
- [x] 8.2 新目录构造三文件固定镜像与原dc8回退，验证237/234、Config/基础层，实际镜像隔离探针通过并记录模拟和本地真实Redis边界。
- [x] 8.3 补专用控制器回归，确认严格TCP0、原七项+CN实体/单writer门禁、最终重复检查、漂移failclosed及受保护恢复，prepare/preflight通过。
- [x] 8.4 用户工作全零、TCP0及所有冻结归属通过后仅切换Backend；工作或连接仍在则等自然结束，不单独断连、不混跑writer，已部署重入只验收。
- [x] 8.5 独立verify及实际输入/配置/Schema/健康/公开路由/Web/助手/七非目标验收，短时脱敏错误与自然流量慢接口分布，记录真实异常与样本限制。
- [x] 8.6 保存脱敏证据、更新实际生产基线/发布记录/任务并通知用户测试，确认其它组件/真实模型/用户任务/账务/Git不变。

第8节生产结果：2026-11-04 04:25:57（北京时间）仅Backend切换a1e6镜像/7663容器，单独verify及约270秒健康/错误观察完成；237/234、203/344/44、d7/辅助/Web366及七非目标通过。严格八项工作/TCP0，无残留例外。验收后自然连接状态159条P95 44.04ms，空闲窗口不承诺高峰收益；10次启动502均前4秒且验收后无新增。见[发布记录](../../../docs/releases/cn-pinned-binding-20261104.1.md)。无其它组件/账务/模型/生产压测或Git操作。
