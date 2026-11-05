# 国服定点读取与连接关闭隔离发布 cn-cleanup-control-20261106.1

状态：**2026-11-06 01:22:18（北京时间）发布完成，独立verify、真实来源/合同验收及短时观察通过。** 用户已授权国服部署并自行测试，本次未提交推送Git。

## 实际来源和发布范围

新鲜核对原a1e6/7663实际237输入，与[本地1013项通过的候选](cn-cleanup-control-local-20261104.1.md)起点一致。仅六改一增，238份新输入中231份原输入逐字保持；从实际镜像只COPY七文件，Config与原基础层保持，没有根目录全量构建或混入未发布的screenshot配套。

实际新镜像 `sha256:1724a4e95c8fe610d2e6b98a5186a3867adde99c4126e96f55920c2beefc80cf`，容器 `df784f8286927f6221b87d963da525243aa278fd92cceaf7767fad137bddb3c1`，StartedAt `2026-11-05T17:21:56.348996183Z`。健康且RestartCount0，在472.25秒观察结束复查仍保持。固定兼容回退为原 `sha256:a1e6c069511c7ea9eefa38cd4fe662400de2d50a19a3a70f9528215ebf0f3cc9`；未回退或重复重启。

专用冻结目录 `/opt/offersteady/releases/20261106-cn-cleanup-control-1`，控制器SHA `01b8b73d00254318aa9458aa24836e5efc713f8ae2179ce28a0408e6ca95a8bd`。七项既有门禁、CN实体九个保护字段全零、TCP8000严格0及单writer/归属证明在prepare/preflight与最终切换重复通过；没有终止用户工作、清活动、单独断连或继承旧TCP例外。原7项失败任务与22条历史孤立预占按原口径保留。任何恢复也须重新空闲并证明归属，禁止旧新writer混跑。

## 已完成验收

发布相关回归146通过、220子用例通过。控制器除固定来源/七文件清单及两处预期计数外，全部生命周期函数AST与已审查基础相同；本次未调用子代理。实际固定镜像在network-none/read-only/cap-drop下通过238输入、162编译、203完整Schema、344有效配置、Python3.13.15/44依赖、辅助上传格式/d7助手及既有功能/新逻辑探针，13个合成线程全部释放。镜像Redis传输为模拟，真实Lua和1/1242/10000规模证据来自本地独占Redis；没有连接生产DB/模型或创建真实用户任务来验收候选。

部署后单独verify和实际来源采集再次通过完整Schema、有效私有配置逐值等价、实际44依赖、辅助格式、助手1.3.6/d7、Web366份文件与七个非目标。私有配置/环境、原始日志及用户标识均留服务器。模型/Prompt、计费、SQL、连接池（false）、依赖、Web/助手/Global/worker保持。

## 真实异常与观察限制

切换启动后0.524–3.545秒之间有**15次真实502**，其中9次实时控制、6次连接状态。全部早于控制器部署验收完成；后续及最近60秒未新增。不能把本次切换描述为完全没有短暂影响。

截至后续472.25秒观察，Backend 1358行中ERROR/CRITICAL、Traceback、HTTP5xx、stream_failed、清理警告及物理关闭失败计数分别为0/0/0/0/0/0。主循环早期窗口保留约1445ms最大漂移，包含启动/发布Schema核验，不能当作稳定面试负载的排队表现或隐去。

在独立来源/配置/公开入口检查全部完成后，另取120.497秒自然窗口：普通HTTP 162条，P95 47.0ms、max 74.53ms，≥500ms为0；容量样本活跃面试/音频均0。此时是空闲轮询流量，不是同类6–7场活跃面试前后对照，不能将47ms或本地合成下降比例承诺为生产高峰效果。没有为补样本调用模型、创建真实面试或生产压测。

当前可交用户测试，重点检查开始/结束、暂停/恢复及重连；高峰API P95和真实音频稳定性仍需正常使用观察。

## 脱敏证据

[production-verification.json](cn-cleanup-control-20261106.1/production-verification.json), [backend-runtime-manifest.json](cn-cleanup-control-20261106.1/backend-runtime-manifest.json), [candidate-probe-result.json](cn-cleanup-control-20261106.1/candidate-probe-result.json), [release-regression-summary.json](cn-cleanup-control-20261106.1/release-regression-summary.json), [controller-source-review.json](cn-cleanup-control-20261106.1/controller-source-review.json), [post-release-error-summary.json](cn-cleanup-control-20261106.1/post-release-error-summary.json), [proxy-error-window.json](cn-cleanup-control-20261106.1/proxy-error-window.json), [post-verification-natural-routes.json](cn-cleanup-control-20261106.1/post-verification-natural-routes.json), [verification-boundary.json](cn-cleanup-control-20261106.1/verification-boundary.json), [production-evidence-review.json](cn-cleanup-control-20261106.1/production-evidence-review.json)

完整控制器、测试JUnit、探针及脱敏汇总保留于 `artifacts/cn-cleanup-control-20261106-release/`。实施见[任务第5节](../../openspec/changes/bound-cn-session-cleanup-and-control-reads/tasks.md)与[生产规范](../../openspec/changes/bound-cn-session-cleanup-and-control-reads/specs/cn-cleanup-control-production/spec.md)。
