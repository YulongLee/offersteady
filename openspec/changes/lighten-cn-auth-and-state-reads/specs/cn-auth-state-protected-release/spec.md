## ADDED Requirements

### Requirement: CN production release requires the new dated authorization and actual runtime binding
2026-10-17 用户已授权将本轮已验收优化部署到国服。系统 SHALL 将此次授权限定到 CN Backend 八文件批准节点，保留此前本地阶段无生产变更的证据；发布 MUST 重新核对当时实际镜像/容器、可写层源码、完整 app/Prompt 清单、路由/OpenAPI、有效配置/模型和非目标组件，MUST NOT 用旧目录、`current`、共享标签或健康版本字符串替代真实运行基线。

#### Scenario: Actual runtime still matches the validated baseline
- **WHEN** 当前 CN Backend 与本地冻结基线、八文件批准差异和候选完整性全部匹配
- **THEN** 可继续复用已验收最小候选及新授权执行本能力规定的发布，原本地验证仍明确记录为历史本地结果

#### Scenario: Runtime or configuration has drifted
- **WHEN** 实际镜像、可写层源、有效配置/模型或部署身份与准备时基线不符
- **THEN** 拒绝直接切换旧候选，先保护实际差异并重新制作/验证同范围最小增量，不覆盖新发布或默默扩大八文件批准范围

### Requirement: The immutable candidate preserves all unrelated runtime behavior
候选 MUST 以实际 CN 镜像为基础，只叠加鉴权 port/service/两仓库、SessionService 和 session/web/realtime_speech 路由模块的已验收批准节点。其他源码、未批准节点、Prompt、模型/配置、既有预取/心跳/ACK、模拟面试收费和期限、助手清单及功能开关 MUST 保持。生产变更前 SHALL 冻结候选完整性证明及不可变原镜像/有效配置回退基线，通过发布合成回归及隔离只读离线 probe。

#### Scenario: The development tree contains unrelated regional code
- **WHEN** 工作区与实际国服源还存在 Global 或其它已开发但未发布差异
- **THEN** 发布仅迁移八文件批准节点，国服原正文/路由和其余源码保持，不从整个工作区整包替换

#### Scenario: Candidate integrity or offline safety check fails
- **WHEN** 任一源码/未批准节点/Prompt/路由/配置保护检查、发布合成回归或离线 probe 失败
- **THEN** 保持原 CN Backend 不变，记录失败，不启动真实模型、真实面试、生产迁移或生产压测

### Requirement: Only an authoritatively idle CN Backend can be switched
系统 MUST 在切换前重复核对部署/候选身份并执行既有只读活动门禁，覆盖普通/笔试/模拟面试、近期准备、网页/桌面租约、音轨/发布者、回答/截图和资料工作。受保护活动非零或结果不确定时 MUST 不重启/不切换，MUST NOT 清理用户记录或放宽门禁制造空闲。切换 SHALL 仅通过版本私有固定镜像 ID overlay 更新 CN Backend，保留有效 Compose 顺序/项目目录、环境、HostConfig、挂载和网络策略；Global、Web、Admin、worker、数据库及助手保持原运行身份。

#### Scenario: A user interview or uncertain gate is present
- **WHEN** 任何受保护活动存在，或活动/身份检查失败、超时或无法权威判断
- **THEN** 拒绝此次 Backend 重启/切换，用户面试与生产记录保持，报告门禁结果

#### Scenario: All immediate activity and identity gates pass
- **WHEN** 重复权威门禁确认无受保护工作且当前部署和候选仍匹配冻结身份
- **THEN** 仅 CN Backend 切换到已验证固定镜像，非目标组件、有效配置、共享标签和源码指针保持

### Requirement: Verify actual release and recover only this release's owned previous Backend
发布后 MUST 核对实际容器健康/重启、源/Prompt/路由/OpenAPI、有效模型/配置、非目标组件身份、匿名公开入口及短时脱敏错误摘要。失败恢复 MUST 检查发布归属、没有后续部署、配置/镜像身份及活动安全，只允许恢复本次冻结原 CN Backend 镜像/配置，随后验证恢复结果；无法确认安全归属时 MUST 不自动覆盖。交付 SHALL 区分线上部署验证与尚未测量的真实 P95/物理客户端验收，不触碰 Git。

#### Scenario: Candidate fails acceptance after switch
- **WHEN** 候选发布后检查失败，且发布归属、无后续部署与活动安全检查全部通过
- **THEN** 仅恢复本次原 CN Backend 镜像/配置，重新核对健康及保护项并记录实际恢复结果

#### Scenario: A later deployment or protected work prevents automatic recovery
- **WHEN** 回退检查发现后续部署、身份漂移、保护活动或不确定状态
- **THEN** 不覆盖当时运行组件，记录并报告实际故障与无法安全恢复的原因

#### Scenario: Release checks succeed without sustained real-user measurements
- **WHEN** 健康、完整性、配置和入口检查通过，但未完成真实面试或持续真实流量对照
- **THEN** 如实记录已部署和验收边界，不宣称真实 P95 或物理收音效果已被证明改善
