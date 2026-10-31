## ADDED Requirements

### Requirement: Release only the authorized fixed CN increments
生产发布 MUST 以新鲜实际运行Backend/Web镜像为基线，仅叠加已自测状态读取和控制查询增量。MUST 保留全部既有面试、简历、多屏、收费、模型、助手和SEO，连接池保持关闭。固定新依赖不得升级其它包；私有配置不得离开服务器。

#### Scenario: Baseline or payload differs
- **WHEN** 容器归属、镜像、配置、完整运行输入或候选载荷与冻结记录不一致
- **THEN** 停止自动切换并报告，不使用旧目录或版本字符串代替实际基线

#### Scenario: Candidate is prepared
- **WHEN** 从实际镜像构建候选和兼容回退
- **THEN** 实际候选源码、依赖、配置和API Schema验证通过，Web旧资源与SEO保持，不连接生产数据或真实供应商进行候选探针

### Requirement: Wait for real user work without bypassing protections
发布 MUST 在无在线面试且完整只读工作门禁通过时执行，MUST 保留准备页、模拟面试、收音、回答、资料、简历、账务及TCP连接保护。MUST 固定原进程启动锚点并重复门禁，MUST NOT 结束面试、删除租约或继承旧准备页例外。

#### Scenario: Any protected work remains
- **WHEN** 发现仍有用户工作或未完成任务
- **THEN** 原服务保持运行并延后发布，未知状态或门禁读取失败停止切换

#### Scenario: All gates pass just before switch
- **WHEN** preflight及最终切换前完整门禁均通过且归属未漂移
- **THEN** 仅按冻结配置更新国服Backend/Web，不更新其它组件或国际服

### Requirement: Verify ownership and recover a failed owned switch
发布 MUST 固定候选及回退镜像，验收运行归属、有效配置、完整API Schema、公开资源、健康及非目标组件。仅对确认属于本次的失败切换执行回退，并核对真实恢复结果。

#### Scenario: Verification fails after an owned cutover
- **WHEN** 本次切换后验收失败且归属仍可证明
- **THEN** 恢复固定旧Backend及兼容旧Web，保留候选新版chunks，核验恢复；恢复失败明确报告

#### Scenario: Successful verification completes
- **WHEN** 运行与公网验收及短时脱敏错误观察完成
- **THEN** 保存真实镜像、工作门禁、范围保护与ERROR/Traceback/HTTP5xx聚合证据，通知用户测试，不将短时观察当成长期性能结论
