## ADDED Requirements

### Requirement: Freeze the actual CN Backend and preserve its hot download manifest
生产阶段 MUST 仅部署四文件已测 CN Backend 增量，MUST 核对实际组件 Id/固定镜像/StartedAt、运行输入、有效配置、依赖及203条完整Schema。MUST 明确证明 c62df 镜像内旧下载清单与 live d7 清单的唯一差异，新候选与固定回退 MUST 保留当前 d7；Web、助手安装包、worker、Global、模型、计费、schema、依赖及 Git MUST 保持。

#### Scenario: Assemble a runtime-equivalent incremental candidate
- **WHEN** 由实际固定镜像构建候选并运行隔离合成探针
- **THEN** 候选233输入仅含四文件允许增量，229非目标保持，Settings/依赖/Schema不变，探针无生产数据库/网络/模型/真实面试调用

#### Scenario: Runtime or private configuration drifts
- **WHEN** 源码、下载清单、配置、Compose来源、控制器/探针/support或实际组件身份发生未批准变化
- **THEN** 停止自动切换并报告，不覆盖漂移、不用旧目录代替实际基线

### Requirement: Cut over only after all existing user-work gates pass
部署 MUST 在 preflight 及最终切换前重复通过原七项只读用户工作门禁和当前 Backend TCP8000 门禁。MUST 保持1792600214792财务历史下界与当前原进程 orphanAnswerContext 分离；MUST NOT 终止用户、清理活动或增加准备页/账务例外。只有 protected_user_work_cutover_deferred MUST 作为正常等待；unknown/读取失败等其它错误 MUST 停止并报告。

#### Scenario: A real interview or preparation page is active
- **WHEN** 任一保护工作或TCP连接仍存在
- **THEN** 原服务保持，等待其自行结束，切换次数为零且不放宽门禁

#### Scenario: Work begins after preflight
- **WHEN** preflight通过后但最终切换前出现新的保护工作
- **THEN** 重复门禁阻止切换，不依赖先前空闲结果

### Requirement: Restrict recovery to proven release ownership
发布 MUST 仅切换固定 Backend 候选，保持七个非目标容器签名和所有私有配置。回退 MUST 使用固定 live232/d7兼容镜像且仅作用于已证明归属的本次候选；原容器仅停止未替换时 MUST 用双重原 Id/Config/Stopped 证明后恢复。未知归属/配置漂移/恢复失败 MUST 停止。已部署重入 MUST 只验证不重复重启。

#### Scenario: Candidate health fails with known ownership
- **WHEN** 本次候选失败且归属、冻结文件及全部保护门禁均核对通过
- **THEN** 尝试固定兼容回退并核验恢复；若验证或恢复失败则停止并通知所需处置

#### Scenario: A different process takes over or release is already complete
- **WHEN** 当前组件属于其它发布，或本次部署已完成
- **THEN** 对其它归属不做切换/回退；对已完成归属只核对真实结果，不重复重启

### Requirement: Verify the live result without real user or provider actions
上线后 MUST 核对固定镜像、全233运行输入、有效配置、完整203Schema、当前下载清单、健康/旧公开路由、七个非目标签名，并独立 verify 与短时脱敏错误统计。MUST NOT 输出凭据、原始用户日志/资料或创建真实面试、模型调用/付款/生产压测。MUST 向用户报告实际结果与观测限制。

#### Scenario: Successful deployment
- **WHEN** 本次切换及独立验收通过
- **THEN** 保存脱敏证据和生产记录，通知用户测试并明确短窗口不代表长期P95收益
