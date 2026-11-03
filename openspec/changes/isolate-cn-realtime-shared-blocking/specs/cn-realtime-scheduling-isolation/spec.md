## ADDED Requirements

### Requirement: Isolate CN synchronous voice work with bounded ordered execution
CN publisher与实时音频连接/引导/接收/断开的同步外部I/O及阻塞锁等待 MUST 脱离主循环，MUST 使用有界资源并按原连接顺序await，慢生命周期工作 MUST NOT 占满既有短控制执行资源。原鉴权、会话/设备状态、收音模式、计费及1.3.6协议 MUST 保持；Global和独立mock legacy分支 MUST 保持。

同样关闭ASR的CN capture-control暂停/恢复 MUST 被隔离，MUST 与同会话结束串行并在执行时重读权威状态，MUST 保留收费及原错误；不得因移到线程使迟到resume复活已结束会话。

CN session end及supersede的直接终止/关闭调用 MUST 整体隔离，MUST 保留原expected_previous、模式、权限及最终读取合同；Global及其它session入口保持。

#### Scenario: Slow source close or Redis during concurrent interviews
- **WHEN** 某连接关闭或候选写被合成阻塞，另一个面试继续发送心跳/音频
- **THEN** 主循环可推进，独立请求继续响应，音频次序和terminal至多接受一次保持

#### Scenario: Legacy and non-target routes
- **WHEN** CN旧音频/frames入口、Global或mock独立入口执行
- **THEN** CN兼容同步工作被隔离，非目标沿原业务校验与wire合同，原错误不得变成成功

#### Scenario: Slow pause and concurrent resume or end
- **WHEN** CN pause关闭来源缓慢，同时收到resume或结束
- **THEN** 无关面试继续调度，同会话控制串行、终止后不恢复，原分钟收费与不足余额错误保持

#### Scenario: End or supersede waits for slow pause
- **WHEN** 用户在慢pause期间结束或按原expected_previous确认替换面试
- **THEN** 终止的锁等待不占主循环，原校验及最终结果保持，错误目标和mock会话仍拒绝

### Requirement: Preserve resource ownership on cancellation and shutdown
未提交取消 MUST 不执行；已提交工作 MUST 不重放，MUST 完成或确定取消后再按序清理。槽位 MUST 在实际worker结束时释放；被取消但创建成功的资源 MUST 恰好一次补偿清理。缺少lifespan执行器的兼容fallback MUST 同样避免晚到资源泄漏。关闭 MUST 停止接纳并不阻塞主循环，MUST NOT 声称可硬杀运行线程。

#### Scenario: Cancel during connect or frame admission
- **WHEN** 连接/创建/帧准备提交后调用者被一次或多次取消
- **THEN** 不提前释放实际占用，不重复业务，成功但弃用的publisher被清理，帧准备不在断开清理后晚到写回

#### Scenario: Saturation and shutdown
- **WHEN** 有界lane满载、外部工作失败或应用关闭
- **THEN** 入场等待、错误和清理可验证，原控制资源可继续运行，无无界线程或静默重放
