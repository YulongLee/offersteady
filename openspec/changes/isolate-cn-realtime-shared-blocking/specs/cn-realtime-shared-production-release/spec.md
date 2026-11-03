## ADDED Requirements

### Requirement: Freeze the actual CN Backend and its twelve-file incremental candidate
已授权生产阶段 MUST 仅更新CN Backend十二文件已测增量。MUST 重新核对实际组件Id、固定镜像、StartedAt、233份已捕获输入、有效私有配置、完整203Schema、依赖和助手d7清单；候选 MUST 为237份输入且225份非目标字节/权限保持。233份 MUST NOT 被描述为所有镜像层文件的完整清单；实际镜像保留的独立上传格式文件 MUST 另行核对。MUST 从固定实际镜像仅叠加允许增量，保留原Config/基础层，不从根目录全量构建或引入其它未发布代码。

#### Scenario: Construct and probe the fixed production candidate
- **WHEN** 基线与十二文件来源核对一致，构造候选及固定原镜像回退
- **THEN** 实际镜像隔离合成探针证明237/225、Schema/344有效Settings/44依赖/Python/上传格式/d7保持，不启动lifespan、不连接生产DB/Redis/模型或创建真实用户工作

#### Scenario: Actual component or frozen source drifts
- **WHEN** 实际组件、源码、镜像、私有配置/Compose来源或控制器/探针/support发生未批准漂移
- **THEN** 停止自动切换并报告，不覆盖漂移、不把旧目录或健康版本字符串当作实际基线

### Requirement: Repeat all protected user-work gates before single-writer cutover
prepare/preflight及最终切换前 MUST 重复原七项只读用户工作门禁、新增第八项cn_entity_idle_gate、当前Backend TCP8000门禁和唯一CN writer证明。新增门禁 MUST 独立只读覆盖新namespace中的binding、candidate、CAS claim及退役/owner/activity元数据，MUST NOT 替代或放宽原七项、触发seed、续TTL、清key或改变claim；未知格式/归属/活动状态或读取失败 MUST fail closed。MUST 保护普通/笔试/模拟、准备页、音轨/发布者、未完成回答/截图、资料/简历与有效账务。财务历史下界1792600214792 MUST 与新鲜原组件Id/StartedAt的orphanAnswerContext分开。只有protected_user_work_cutover_deferred MUST 视为正常等待；unknown/读取失败 MUST 停止。MUST NOT 终止用户、清理活动、放宽八项工作门禁或增加准备页例外；TCP默认零连接仅允许下述明确授权的精确原Backend单条残留TCP例外。

#### Scenario: Existing or newly started user work blocks release
- **WHEN** 任一保护工作仍在、TCP不满足下述精确原Backend例外或默认零连接要求，或preflight后出现新工作
- **THEN** 原服务保持，切换次数为零并等待用户自行结束，最终门禁不复用旧空闲结论

#### Scenario: Legacy gates are idle but new CN entity work remains
- **WHEN** 原七项通过，但新namespace仍有保护binding/candidate claim，或其退役/owner/activity元数据无法安全分类
- **THEN** 独立第八项阻止切换及回退，忙碌则等待，unknown或读取失败则停止报告，不以旧snapshot空闲覆盖新实体状态

#### Scenario: All gates pass and the writer is exclusively owned
- **WHEN** 冻结来源、实际归属、全部空闲门禁及唯一writer均核对通过
- **THEN** 仅先停止原Backend再启动固定候选，不允许旧snapshot writer与新entity writer同时运行，七个非目标组件保持

### Requirement: Honor only the explicitly authorized original Backend residual TCP exception
2026-11-04用户已明确授权继续部署，并接受原服务最多一条残留连接随正常更新断开。TCP门禁 MUST 默认要求0；只有尚未切换、非recovery/rollback，运行容器精确Id为035642d58f7eb9ad16f46a830d153130b1d2d6e7851401b0ec620cdaeed101bf、固定镜像精确为sha256:5efba4abea9b12e1af2b9d2c6e8f6edb2c205afed93f4f9fc9ba862e96499229，原七项与新增CN实体保护工作全零，读取/owner/单writer/来源与冻结材料全部验证成功时，MUST 允许原服务TCP为0或1。MUST 在preflight与最终切换前重新证明全部条件。TCP大于1、新工作、unknown、读取失败或任何证明不符 MUST 阻止切换。新候选、已切换后及所有恢复/回退 MUST 仍严格TCP为0，MUST NOT 继承本例外。MUST NOT 单独断连、清状态或改变八项工作门禁，仅可通过正常固定Backend部署处理残留连接。

#### Scenario: Precisely owned original service has one residual connection
- **WHEN** 原Id/image、未切换且非recovery与所有保护工作为零及读取/归属/来源证明均通过，原服务TCP为1
- **THEN** 正常部署可继续并使该残留连接随更新断开重连，不单独杀连接或清理状态

#### Scenario: Residual exception cannot be established or recovery is requested
- **WHEN** TCP大于1、新工作/unknown/读取失败/身份来源不符，或目标为新候选/已切换后/任何recovery或rollback
- **THEN** 不套用原服务例外；前述不符阻止切换，新候选及恢复路径只有严格TCP0且其它全部门禁通过才允许继续

### Requirement: Protect new entity state and recheck idle ownership before any recovery
新候选 MUST 使用独立CN binding namespace，旧snapshot/v1绑定仅作兼容seed并保留字节；MUST NOT 清空Redis、回写旧snapshot或声称旧binary能读取新entity的活跃变更。任何失败回退 MUST 先重新证明本次发布归属、冻结配置/来源、单writer和原七项+新增CN实体+严格TCP0全部门禁空闲，再使用固定原镜像；MUST NOT 继承原服务单条残留TCP例外或在新候选已接纳活跃工作时回退。未知归属/漂移/读取或恢复失败 MUST 停止并通知。

#### Scenario: Candidate fails after accepting protected work
- **WHEN** 本次候选健康或验收失败，且仍有保护工作或无法证明空闲
- **THEN** 不切换到旧binary，不终止/清理用户工作，报告并等待安全处置，不以旧key仍在声称活跃回退兼容

#### Scenario: Known candidate is idle or the original container was only stopped
- **WHEN** 固定输入、归属及重新执行的全部门禁通过
- **THEN** 已知本次候选可停止后恢复固定原镜像；原容器仅停止未替换时另须双重原Id/Config/Stopped证明才恢复，不同时运行旧新writer

#### Scenario: Release is already deployed or another release owns the process
- **WHEN** 重入发现本次已部署，或当前组件属于其它发布
- **THEN** 对本次已部署只验证真实结果、不重复重启；对其它归属不执行切换或回退

### Requirement: Verify the real result and preserve non-target components and privacy
发布后 MUST 独立verify固定镜像/237输入/225保持、有效私有配置、完整Schema/依赖/Python、上传格式/d7、健康/重启、原公开路由、Web公开文件及七个非目标签名，并保存短时服务器侧ERROR/CRITICAL/traceback/HTTP5xx脱敏统计和新增数值观测。MUST 如实报告异常与短窗口限制。Web、助手、国际服、worker、模型/Prompt、收费、SQL结构/索引、依赖、池开关及Git MUST 保持。诊断 MUST 仅只读汇总；私有配置/凭据及原始用户日志/材料/音频/标识 MUST 留服务器，MUST NOT 调真实模型、创建真实面试/付款或生产压测。

#### Scenario: Deployment and independent verification complete
- **WHEN** 真实切换、独立验收和短时聚合完成
- **THEN** 保存脱敏证据并更新实际生产发布记录/任务，通知用户测试，明确本地测试与短时线上窗口不能推算长期整体P95
