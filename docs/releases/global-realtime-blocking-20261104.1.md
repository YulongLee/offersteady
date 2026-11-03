# 国际服实时共享阻塞优化 global-realtime-blocking-20261104.1

状态：**2026-11-04 05:40:36（北京时间）仅Global Backend发布完成，单独verify、实际来源/完整合同及短时错误观察通过。** 用户同时授权随后Git封版，结果见[release-20261104.1](../../releases/20261104.1/README.md)。

## 实际来源和范围

从实际Global Backend固定c68c315镜像、852d46容器的303份输入出发，与该镜像和11月2日独立公开封存逐字匹配。新固定镜像 `sha256:457a18eb4eec92857e76200f7a3139983a70838a01be66bde97f4d5d58650abf`，容器 `efecd3922acf506645a56a3d5f66423716afcd2889934c6cd916dd30eb175df5`，StartedAt `2026-11-03T21:40:11.677452684Z`。当前307输入：8份既有文件增量、4个内部模块，295份旧输入保持。原c68为固定回退，未回退或重复重启。

同步本日CN已验证的有界音频ingress/lifecycle隔离、取消后drain及一次补偿、同场捕获/结束/替换串行、实体原子状态和退役fence、请求内资料批读/去重、完整pin的定点原子读取。Global原轻control投影、1.5秒成功状态缓存、异步ASR关闭和WS终态处理保留。Global缺少的cleanup-lock引用计数作为必要依赖适配；supersede增加实体退役清理并保留历史转录。

未移植CN独立device-status投影或CN reaper/计费行为，没有修改模型/Prompt、时间会员/Creem、语言、功能开关、SQL结构/索引、连接池、依赖或生产配置。Web251文件、助手Global1.3.6清单/历史下载、worker267输入及七非目标签名保持，国服a1e6镜像及237/196/366三组件也已新鲜只读复核保持。没有更新安装包，用户无需重装助手。

## 验证与发布保护

最终合成回归：149性能/实体/真实本地Redis与PostgreSQL测试、204既有Global业务测试、114额外Global模拟面试HTTP/WS/清理/语音生命周期测试通过；原业务集合中4项专用PostgreSQL测试未选入，未描述为已执行。控制器及复用基础154项通过；已有非目标函数AST保护通过。测试夹具已按Global实际事件和可选批读接口修正，不以无限制Mock代替真实方法。

1/1191/10000合成历史下完整pin均3次Redis传输、1份绑定解码、1次权威control读，命中路径客户端和Redis服务端HVALS/HGETALL/HSCAN增量0；12个混合轮询及retire/rebind交错通过。以上是真实独占本地Redis，不换算线上P95。

实际固定镜像在network-none/read-only/cap-drop下验证307份输入、171 Python编译、Python3.13.16/46依赖、379有效Settings和223完整Schema、辅助上传格式和Global助手清单保持。合成慢关闭、取消/关闭补偿、metadata/mode/pin场景通过，9个线程全部释放。探针使用脚本化Redis传输，没有在镜像探针内执行真实Lua；Lua由本地专用Redis验证。无lifespan、生产数据库/模型/付款/面试调用或生产压测。

新冻结目录 `/opt/offersteady-global/releases/20261104-global-realtime-blocking-1`，控制器SHA `8653e8f1e171a0f40edb780bd5678435a756f39f884dee6ce9a74a8fd9292170`。prepare/preflight和最终切换重复原七项Global用户工作门禁、实体namespace只读保护、严格TCP8000=0、单writer与冻结来源归属。没有残留连接例外、结束用户或清活动。未知/读取失败/漂移停止；任何恢复仍须同样全量门禁，禁止新旧writer混跑。34条既有公开路由/资产字节及匿名边界保持：state14字段、sessions/mock401、公开openapi/index.html原404。

## 短时生产结果及限制

截至启动后约164秒，Backend/Web自启动、验收后及最近60秒的ERROR/CRITICAL、traceback、HTTP5xx、stream_failed和清理警告均0，健康且RestartCount0。验收时一次内部Schema冷生成2048.83ms与早期1962.795ms主循环漂移如实保留；随后512样本窗口loop P95约1.745ms、max3.884ms。loop调度数据不是API P95。

验收后普通HTTP只有3条，包含本次主动的匿名边界验收请求；不能用其147.67ms最大值作为真实用户P95或宣称固定降幅。真实面试高峰、长期P95和物理设备表现仍待正常使用监控，不通过生产压测制造样本。生产私有配置、原始日志及用户资料/标识均留服务器。

## 证据和恢复

[实际验收](global-realtime-blocking-20261104.1/production-verification.json)、[完整输入](global-realtime-blocking-20261104.1/backend-runtime-manifest.json)、[实际镜像探针](global-realtime-blocking-20261104.1/candidate-probe-result.json)、[合成汇总](global-realtime-blocking-20261104.1/regression-summary.json)、[真实Redis规模](global-realtime-blocking-20261104.1/synthetic-scale-cost.json)、[短时错误](global-realtime-blocking-20261104.1/post-release-error-summary.json)、[匿名边界](global-realtime-blocking-20261104.1/public-boundary.json)、[国服保持](global-realtime-blocking-20261104.1/cn-preservation.json)。[Spec任务](../../openspec/changes/sync-global-realtime-blocking-20261104/tasks.md)与[单独恢复快照](../../releases/20261104.1/README.md)绑定实际区域来源；旧控制器和目录不能直接重放。本地完整脱敏执行记录在 `artifacts/global-realtime-blocking-20261104/`。
