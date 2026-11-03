## ADDED Requirements

### Requirement: Dispatch CN device status work without blocking the event loop
国服 `device-status` 的同步绑定解析与发布 MUST 作为一个工作单元交由既有控制执行器执行，MUST NOT 在 asyncio 主循环等待同步仓库；现有队列/线程上限及 fallback MUST 保持，不重放失败或取消的工作。Global MUST 保持既有业务路径。

#### Scenario: Slow synchronous repository
- **WHEN** 国服设备状态仓库被合成阻塞，而其它协程等待运行
- **THEN** 其它协程仍可推进，状态事件最多保存一次且返回原合同

#### Scenario: Worker fails or caller cancels
- **WHEN** 工作抛出领域错误或调用者取消等待
- **THEN** 保持错误/取消传播，不重放业务，工作线程计时作用域最终清理

### Requirement: Preserve authoritative binding and status contracts with lightweight reads
国服设备状态专用路径 MUST 复用既有权威会话控制投影，不加载资料、不刷新或写回会话。MUST 保留原解析 fallback、绑定状态/generation/心跳时限、session owner/存在与 preparing/live 检查，以及最终发布独立的 owner/存在检查；MUST NOT 引入跨请求权限缓存或新增状态门禁。原 payload 过滤与事件保存 MUST 等价。

#### Scenario: Device with many bound materials
- **WHEN** 合法带手动码的国服设备发布状态，关联多份资料
- **THEN** 两处会话校验均读取必要控制字段，完整会话/资料读取和会话写回均为零，事件与原实现等价

#### Scenario: Invalid stale replaced or foreign binding
- **WHEN** 设备缺失、fallback 命中、绑定不活跃、generation 不符、心跳过期、会话不存在/删除/外用户或绑定其它会话
- **THEN** 按原逻辑返回同一结果或 404/403/410 错误，不泄露其它用户内容

#### Scenario: Session changes after first check or between requests
- **WHEN** 会话在校验后删除/结束，或下一请求的绑定、generation、owner、状态发生变化
- **THEN** 保留原最终 owner/存在校验及发布状态语义，后续请求读取当前权威状态而非旧缓存

#### Scenario: Legacy authenticated status and other operations
- **WHEN** 未提供手动码的合法请求，或 Global、其它控制、普通/笔试/模拟面试发起原业务操作
- **THEN** 认证/显式 userId 冲突及事件合同保持，非目标仍沿原完整业务校验

### Requirement: Sample private bounded phase timings
系统 MUST 仅对低比例的国服设备状态工作输出私有分段观测，区分排队、DB 获取/执行/取数及绑定/事件仓库操作；MUST 使用固定字段与受限状态、单调非负有限数值。MUST NOT 记录用户/设备/会话/请求标识、资料、SQL/参数、凭据、原始 payload 或异常文本。作用域、采样及记录故障 MUST NOT 影响业务结果；其它请求与 Global MUST 不启用本观测。

#### Scenario: Sampled concurrent work
- **WHEN** 选中的工作包含数据库和仓库阶段，且多个工作并发
- **THEN** 每条样本只含本次工作相位，线程复用后无残留；DB acquire 不包含 execute/fetch，标签明确仓库时长非纯网络及样本不含认证/HTTP 阶段

#### Scenario: Unselected work and broken observer
- **WHEN** 工作未被采样，或计时/日志组件失败
- **THEN** 不增长用户维度状态，不输出未采样日志，业务结果及异常保持

### Requirement: Deliver a baseline-preserving local candidate
本轮 MUST 仅本地开发自测，以封存实际国服 232 输入为基线且仅加入本轮允许文件；MUST 保留完整 203 API Schema、旧笔试行为、助手清单、配置与所有非目标输入。MUST NOT 部署、重启、修改真实用户或提交推送。

#### Scenario: Assemble and verify candidate
- **WHEN** 从封存归档组装本地候选并运行合成回归
- **THEN** 未改文件 SHA 全等、完整 Schema 等价、相关权限/绑定/普通笔试模拟与计费回归通过，记录实际验证和限制，不把本地收益描述为线上 P95 降幅
