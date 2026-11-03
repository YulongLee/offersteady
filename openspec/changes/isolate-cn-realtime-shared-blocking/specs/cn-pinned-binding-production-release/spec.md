## ADDED Requirements

### Requirement: Release only the reviewed three-file CN pinned-binding repair from the actual current image
本次生产 MUST 以重新核对的实际dc8固定Backend镜像及7849容器、237输入为基线，仅叠加已测三文件，保持234非目标字节/权限、Config/基础层、203完整Schema/344有效配置/44依赖、上传格式/d7助手/366Web及七个非目标。MUST 使用新冻结目录及专用控制器，MUST NOT 从根目录全量构建或重放旧控制器/其残留TCP例外。漂移 MUST 停止。

#### Scenario: Build and test the actual minimal candidate
- **WHEN** 新鲜来源及三文件SHA核对通过
- **THEN** 构造固定镜像，network-none/read-only合成探针验证输入/合同和固定pin常数读取；明确真实Lua规模证据来自本地独占Redis，不连接生产DB/模型或创建真实用户任务

### Requirement: Preserve strict idle ownership and protected recovery
prepare/preflight/最终切换及任何恢复 MUST 重新执行原七项、CN实体门禁、TCP8000严格0及单writer/归属证明。MUST NOT 继承第6节旧原容器的单TCP例外，终止用户、清活动、断连或放宽阈值。只允许protected_user_work_cutover_deferred正常等待；未知/读取失败/漂移 MUST 停止。回退固定dc8且只有重新空闲才允许，新旧writer MUST NOT 混跑。

#### Scenario: User work or a connection remains
- **WHEN** 任一保护工作非零、TCP非零或归属未知
- **THEN** 保持服务，等待真实用户自行结束；未知/读取失败报告处理，不执行切换

#### Scenario: Final checks pass or deployment is already complete
- **WHEN** 所有门禁与冻结来源通过，或重入发现本次已部署
- **THEN** 前者仅正常替换CN Backend，后者只核对真实归属/结果不重复重启；恢复也重复全部保护

### Requirement: Verify the actual release and report honest route observations
发布后 MUST 独立verify固定镜像、237/234、完整合同/配置/健康及非目标，短时汇总ERROR/traceback/HTTP5xx及自然active-connection请求分布。MUST 区分启动窗口与稳定窗口、5分钟滚动旧样本和样本不足；没有自然有效pin流量 MUST NOT 补造P95收益或承诺本地时延。私有配置/原日志/标识 MUST 留服务器，不调用真实模型、不创建真实面试/付款、不生产压测，不更新Web/助手/Global/worker/模型/收费/池/SQL结构/依赖或Git。

#### Scenario: Deployment verification and handoff complete
- **WHEN** 真实归属/合同/健康核对及有限自然流量观察完成
- **THEN** 保存脱敏证据、更新实际基线/生产记录和任务，明确异常与限制并通知用户测试
