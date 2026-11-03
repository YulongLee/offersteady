## Context

只读现场已证明Global Backend仍是c68c315镜像、852d46容器，303运行输入与其实际镜像及11月2日公开封存逐字一致。有效Settings379、完整API223路径、七非目标签名已冻结，私有值只留服务器。对比表明仍有snapshot全局锁写、完整pin列表读取和同步音频入口；已有Global异步ASR关闭、1.5秒状态缓存和轻control投影保留。

## Goals / Non-Goals

目标为同步今天CN有界音频执行、实体状态原子更新、资料请求内批读和完整pin定点读取，并保留全部Global合同。非目标为Web/助手/worker/CN更新、麦克风调音、模型/Prompt、依赖、SQL结构、池或收费/语言/功能开关变化。用户已授权同步、自测、生产部署及其后的Git封版；无需重复产品审批。

## Decisions

1. 状态apply-ready。只从实际Global303输入构造独立候选，不把根目录CN完整文件覆盖Global。按CN before/after变更和Global AST差异移植下述节点，所有其它方法保持；出现新增依赖必须在本节补充审查。
2. 允许名单：main仅包装Global实时执行器lifespan；realtime_speech模块的音频准备/帧/连接/捕获控制及数值观测；session模块end/supersede；realtime_speech_service仅捕获串行、候选CAS和pin getter；redis_realtime_speech_repository仅实体原子路径/seed/fence/pin及必要终态清理；session_service仅非mock本次资料预填；knowledge_retrieval仅本次metadata批读；postgres_material_persistence仅可选get_by_ids。四个CN已测内部entity/executor/lifespan/loop模块作为独立Global候选输入，作用域条件适配Global，内部历史类名保留以降低移植差异。新namespace只存在Global独立Redis，不改变旧snapshot内容/协议。
3. 保留Global原有终态WS错误处理、关闭方式、mock/简历runtime、admin/commerce路由及Settings；仅新增路径的CN版条件改为Global。会员/付款逻辑、模型选择和Prompt不移植。
4. 每次操作内批读保持owner/version/missing和fingerprint新鲜度检查，无跨请求资料缓存。实体原子更新避免持有进程全局锁跨网络；回退只能在所有工作空闲、单writer且来源归属证明时使用冻结原c68镜像。旧snapshot只seed，退役fence防止复活。
5. 有效pin命中通过session-owner索引+canonical绑定原子定点读取，保留device/code/session/binding/generation/DB状态和最新fallback。1/1191/10000合成历史验证传输/服务端扫描/解码固定，无全站HVALS后过滤的命中路径。旧仓库fallback保持。
6. 发布新固定目录及专用控制器，复用已审查Global冻结/归属/七项工作门禁，加实体namespace只读门禁，TCP严格0、单writer；准备、最终切换及恢复都重复。unknown/drift/读失败停止，忙时等待自然结束，不终止或清理用户。只能Backend固定镜像变化，静态代理若IP变化仅校验后reload，Web字节/容器不变。
7. 实际镜像探针无网络/read-only、不启动lifespan，完整303+新输入/223Schema/379配置/依赖/辅助格式/Global136清单及非目标保持。另运行本地独占Redis的真实Lua和规模/交错合成回归及Global会员/commerce/普通/笔试/mock/语言测试。自然短窗口不承诺长期P95或真实硬件效果。
8. 先独立verify及短时脱敏错误/自然请求验收，再Git封版。两服源码独立公开归档，各自manifest绑定实际镜像；保留未上线研发差异说明。Git不包含私有配置/原始日志/用户标识/安装包。检查远端版本存在后新建codex分支、普通commit/push和不可变tag，无force。

## Risks / Trade-offs

允许节点依赖补充（实现前审查）：Global旧版本缺少CN捕获串行依赖的cleanup-lock引用计数方法。需在realtime_speech_service新增两个已测lock acquire/release helper与引用数字段，原Global end/supersede函数包装同一锁及finally释放，原清理索引不删除仍有引用的锁。supersede在原reset后增加实体clear以建立持久退役fence，原终态事件仍形成响应但退役后安全丢弃不再复活stream，保留review转录。防止pause/end/supersede重叠时产生两把锁或晚回调复活；不移植CN其它reaper或收费行为。

- Global与CN结构不同 → 函数差异审查、其它AST/字节保护和完整Global合同回归。
- Lua或取消交错造成状态复活 → 继承已测owner/版本/retirement语义，真实本地Redis验证，单writer闲置切换。
- 启动短暂HTTP错误 → 暂无用户工作时切换，记录真实启动及验收后窗口，不能宣称零影响。
- 生产有连接 → 保持原服务等待；无授权中断或残留连接例外。

## Migration Plan

现场来源冻结 → 最小节点适配 → 本地业务/规模/取消测试 → 固定镜像隔离探针 → 重复用户工作/TCP/来源门禁 → 单Backend切换 → 独立实际合同与错误观察 → 记录两服独立基线 → Git封版。

## Open Questions

无待用户决定范围；若观察与冻结事实漂移，停止切换并报告实际所需处置。
