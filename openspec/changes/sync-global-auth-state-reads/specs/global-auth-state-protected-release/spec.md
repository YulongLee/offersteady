## ADDED Requirements

### Requirement: Bind actual Global runtime and preserve the regional contract
发布 MUST 读取实际 Global Image/容器、裸镜像/可写层全源/Prompt、有效模型/配置、完整 HTTP 路径/方法及 OpenAPI、部署上下文和所有非目标组件，不得用旧目录/版本/共享标签代替。候选 MUST 只迁移八文件批准节点，其他文件及未批准节点保持；Global 七天及以上购买套餐准入、UTC 三场、无 CN 积分钱包/60 分钟截止、Creem、语言/Prompt、助手清单和原 mock false 开关 MUST 保留。

#### Scenario: Actual runtime differs from a historical release or development tree
- **WHEN** 当前实际 Global 与历史 b31a 镜像或工作区有额外差异
- **THEN** 重新保护实际差异并验证同范围最小候选，不覆盖区域实现或迁入 CN 商业/语言行为，未重核前不声明已匹配

#### Scenario: Global source and policy protection are checked
- **WHEN** 比较基线与候选并执行合成 Global 权益/账号/语言/Creem/预取回归
- **THEN** 八文件之外及非批准节点、所有 Prompt/有效模型/配置与区域政策保持，隔离测试启用模拟功能不改变线上 false

### Requirement: Freeze and validate the real candidate before production mutation
发布 MUST 冻结载荷/证明与原不可变镜像/有效配置回退基线，使用纯合成本地数据执行安全竞争、SQL/写行计数、ASGI/区域/既有性能和发布回归，并通过禁止网络/DB/写文件/worker/lifecycle 的隔离候选 probe。离线业务 shell 和真实完整应用路由/schema MUST 分别绑定，不得套用 CN 195 或旧 Global shell 数量。失败 MUST 保持原服务。

#### Scenario: A hidden full-app route or schema drifts
- **WHEN** 离线 shell 通过但实际完整应用丢失/新增路由或 schema 不符
- **THEN** 发布拒绝切换，不因 shell 路由数相同而认为完整应用保持

#### Scenario: Candidate or synthetic validation fails
- **WHEN** 源/节点/Prompt/模型/配置/载荷完整性、任何必需自测或隔离 probe 失败
- **THEN** 不切换 Global Backend，记录实际失败和旧基线差异，不用真实用户数据或真实供应商补测

### Requirement: Switch only the Global Backend when protected work is absent
切换前 MUST 重复核对当前部署/候选身份及权威只读活动门禁，覆盖普通/笔试/模拟、准备/租约、音轨/发布者、回答/截图和资料工作；非零、未知、过期采样或读取失败 MUST 拒绝重启/切换，不得清记录制造空闲。通过后 SHALL 仅私有固定镜像 ID overlay 更新 Global Backend，保持实际 Compose 顺序/项目目录、环境/HostConfig/挂载/网络及非目标组件/共享标签/源码指针。

#### Scenario: Protected or indeterminate activity is observed
- **WHEN** 任一受保护活动存在或门禁结果无法权威确认
- **THEN** 保持原组件运行及用户记录，等待真实安全空闲，不执行切换

#### Scenario: Immediate gates and identity checks pass
- **WHEN** 重复门禁通过且部署/候选仍匹配冻结身份
- **THEN** 仅 Global Backend 切到受验固定镜像，CN 及 Global Web/Admin/worker/数据库/Redis/助手保持

### Requirement: Recovery uses independent frozen-baseline activity checks and strict ownership
失败恢复 MUST 核对本次容器/配置归属及无后续发布，并执行冻结原镜像/原环境/网络的独立只读活动门禁；MUST NOT 要求故障候选自身健康/可 import 或信任其漂移环境。私有恢复上下文漂移、新保护活动或归属不明 MUST 停止覆盖；安全时只恢复本次原 Global Backend 并验证结果。

#### Scenario: Candidate health or environment fails after cutover
- **WHEN** 候选验收失败但本次归属明确、冻结恢复上下文未漂移且独立活动门禁通过
- **THEN** 仅恢复固定原 Backend 镜像/有效配置并复核，恢复门禁不依赖故障候选

#### Scenario: Later deployment or new work prevents recovery
- **WHEN** 有后续发布、外来容器/配置、恢复上下文漂移、新受保护工作或未知结果
- **THEN** 拒绝自动或手工覆盖，记录实际状态和无法安全恢复原因

### Requirement: Verify the actual rollout without claiming unmeasured user benefit
发布后 MUST 独立核对实际健康/重启、全源/Prompt/完整路由/schema、有效模型/配置、非目标身份、Global 匿名入口/会员目录/mock false/Web 标识及短时脱敏错误；SHALL 记录真实结果与合成范围。MUST NOT 将短时健康或合成计数当作真实 P95/物理客户端收益，不提交/推送 Git。

#### Scenario: Checks pass without real-user load or hardware testing
- **WHEN** 实际发布验收通过但没有持续真实流量、实体麦克风或真实模型验收
- **THEN** 记录部署事实、公开接口及配置一致性和观察窗口，并明确真实 P95/用户体验仍待后续流量验证
