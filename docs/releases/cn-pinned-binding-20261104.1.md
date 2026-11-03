# 国服固定绑定查询修复发布 cn-pinned-binding-20261104.1

状态：**2026-11-04 04:25:57（北京时间）发布完成，单独verify、实际来源/合同验收及短时自然流量观察通过。**

## 实际基线与范围

原实际dc8镜像/7849容器的237输入经新鲜只读核对，仅叠加[已测三文件修复](cn-pinned-binding-local-20261104.1.md)，234份非目标字节和权限保持。新固定镜像 `sha256:a1e6c069511c7ea9eefa38cd4fe662400de2d50a19a3a70f9528215ebf0f3cc9`，实际容器 `766377a1893425c2d0ce2e20de35c83e29c5cf4b96b1bacf6296e5270bfcdc3c`，StartedAt `2026-11-03T20:25:36.091960008Z`，healthy、RestartCount0在约269.96秒观察结束复查仍保持。固定兼容回退为原dc8，未回退或重复重启。

新冻结目录 `/opt/offersteady/releases/20261104-cn-pinned-binding-1`，控制器SHA `6412b38a65d2d6e05a227f2e2287a89537057ea6cef1613a5eff47e6ed56d236`。从实际镜像只COPY三文件，Config/基础层保持；不使用根目录全量构建，不重放旧发布。完整203 Schema、344有效生产配置、Python3.13.15/44依赖、单独上传格式JSON、助手1.3.6/d7、Web366文件及七非目标保持。私有配置、环境及原始日志/标识留服务器，没有Git提交/推送。

## 验证与切换保护

本地候选相关回归986通过/1项已知Global专属跳过，额外2个屏障交错用例通过。专用控制器、原安全基础及探针回归146项、216子用例通过。控制器除来源/三文件范围及更严格的门禁外，其余生命周期函数AST与前次已审查基础相同；本次来源复核由主代理完成，未调用新的子代理审查。

实际固定镜像以network-none/read-only/cap-drop运行探针：237输入、161编译、203完整Schema、344有效配置、44依赖、上传格式/d7及既有调度/取消/资料/模式场景通过；新getter/service在三种模拟规模均3次传输，身份/退休/精度检查通过。镜像中Redis传输为模拟，没有执行真实Lua；真实Lua和1/1191/10000规模证据来自独占本地Redis。9个合成线程全部释放，未启动lifespan，DB/网络/文件写/真实模型/用户任务均0。

prepare/preflight及最终停旧前原七项门禁、CN实体九个保护字段全零、TCP8000严格0、单writer与归属均通过。1191份历史实体及原7失败任务/22历史孤立预占按原口径保留，没有清活动或单独断连；旧发布单TCP例外未继承。只替换Backend，新旧writer未混跑。任何恢复仍需重新通过全部空闲/来源/归属保护，不能在新版本接纳用户工作时回退。

## 自然流量与真实异常

发布前5分钟空闲自然轮询，active-connection 259条：p50 237.46ms、P95 469.27ms、max 658.08ms。验收完成1秒后至2026-11-04 04:28:40约161.77秒：该接口159条，p50 25.36ms、**P95 44.04ms**、max 90.77ms，≥500ms为0；代理159次均200，95次带双pin/64次不带，共11个不同设备路径。全部276普通HTTP的P95 43.64ms、max 100.83ms，最新后台容量API P95 46.26ms、错误率0、活跃面试0。

两侧是不同长度的空闲自然窗口，不是活跃面试高负载匹配比较；参数形状汇总不是逐请求pin追踪，不能承诺高峰固定降幅。未创建真实面试、调用模型或生产压测来制造样本。

约269.96秒观察中Backend951行的ERROR/CRITICAL、Traceback、HTTP5xx、stream_failed及清理警告均0。**Web有10次真实502**，集中于启动后0.273–3.771秒（4次连接状态、6次其它实时控制），全部早于验收完成；截至2026-11-04 04:30:00验收后及最近60秒均无新增。不能将切换描述为完全无影响。

验收期间另有一次API Schema生成请求1562.85ms，在发布验收完成前；早期主循环摘要保留1464.537ms漂移，后续有界窗口p95约1.975ms、max2.488ms。调度样本不是API P95。最初按启动15秒后采集仍含Schema校验，正式自然窗口改为验收完成后，原始观察也保留，未隐藏慢样本。

## 交付边界与证据

没有改Web/助手/Global/worker、模型/Prompt、收费、SQL结构/索引、池开关、依赖或私有配置，没有终止用户、付款、真实模型调用、生产压测或Git操作。助手无需升级；当前可交用户测试，真实面试与长时稳定性仍需正常使用观察。

[实际验收](cn-pinned-binding-20261104.1/production-verification.json)、[237输入](cn-pinned-binding-20261104.1/backend-runtime-manifest.json)、[实际镜像探针](cn-pinned-binding-20261104.1/candidate-probe-result.json)、[发布回归](cn-pinned-binding-20261104.1/release-regression-summary.json)、[控制器来源审查](cn-pinned-binding-20261104.1/controller-source-review.json)、[发布前自然请求](cn-pinned-binding-20261104.1/pre-release-routes.json)、[验收后自然请求](cn-pinned-binding-20261104.1/post-release-routes-after-verify.json)、[短时错误](cn-pinned-binding-20261104.1/post-release-error-summary.json)、[502窗口](cn-pinned-binding-20261104.1/proxy-error-window.json)、[Schema慢请求归类](cn-pinned-binding-20261104.1/startup-slow-request-category.json)、[证据复核](cn-pinned-binding-20261104.1/production-evidence-review.json)。完整脱敏证据、控制器、探针和JUnit位于 `artifacts/cn-pinned-binding-20261104-release/`。

实施见[任务第8节](../../openspec/changes/isolate-cn-realtime-shared-blocking/tasks.md)与[生产Spec](../../openspec/changes/isolate-cn-realtime-shared-blocking/specs/cn-pinned-binding-production-release/spec.md)。
