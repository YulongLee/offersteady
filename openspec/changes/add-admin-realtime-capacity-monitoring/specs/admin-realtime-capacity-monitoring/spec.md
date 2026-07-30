## ADDED Requirements

### Requirement: Sample real capacity signals

系统 SHALL 定期采样有效进行中面试、在线网页、在线助手、活跃音频流、容器 CPU/内存、数据库连接、API P95 和服务端错误率。

#### Scenario: Active interview is counted
- **WHEN** 面试状态为 live、未删除且最近活动时间未超过闲置关闭阈值
- **THEN** 系统将其计入当前进行中面试数

#### Scenario: Stale runtime state exists
- **WHEN** 网页、助手、发布器或音频帧超过对应新鲜度
- **THEN** 系统不得将其计入当前实时并发

### Requirement: Keep monitoring off the user path

容量采集 MUST 独立于用户请求执行，采集失败 MUST NOT 阻断面试、ASR、回答、支付或资料处理。

#### Scenario: A telemetry source is unavailable
- **WHEN** Redis、数据库或 cgroup 指标读取失败
- **THEN** 对应指标标记为不可用，其他指标和用户功能继续工作

### Requirement: Retain only aggregate capacity history

系统 SHALL 保留近期容量聚合样本，且 MUST NOT 在样本中写入用户、设备、会话、音频、对话或请求正文。

#### Scenario: Capacity sample is persisted
- **WHEN** 定时采样完成
- **THEN** Redis 只保存时间戳和允许的聚合数值，并在保留期后自动清理

### Requirement: Restrict capacity visibility

系统 SHALL 仅允许具有 `observability.read` 权限的管理员读取容量信息。

#### Scenario: Unauthorized request
- **WHEN** 普通用户或无有效管理会话的请求访问容量接口
- **THEN** 系统拒绝访问且不返回任何容量数据

### Requirement: Visualize current state and recent curves

管理平台 SHALL 展示容量当前值、状态阈值、最近 60 分钟横纵坐标曲线、更新时间和数据不可用状态。

#### Scenario: Operator opens operations overview
- **WHEN** 管理员进入运营总览
- **THEN** 页面加载容量监控并定期刷新，且保留现有即时卡片和历史运营趋势

#### Scenario: Capacity loading fails
- **WHEN** 容量接口暂时不可用
- **THEN** 容量区块显示可重试状态，其他后台内容仍可使用
