## ADDED Requirements

### Requirement: Track authoritative interview activity
系统 SHALL 在有效音频帧、回答提交、截图回答提交、开始面试和用户确认继续时更新服务端权威活动时间，MUST NOT 因普通页面轮询、后台查询或积分数值未变化而错误更新或停止活动计时。

#### Scenario: Member generates a zero-point answer
- **WHEN** 有效会员用户成功提交回答且本次扣点为 0
- **THEN** 系统仍将该回答记录为有效业务活动并刷新空闲截止时间

#### Scenario: Browser only polls state
- **WHEN** 页面持续轮询但没有音频、回答、截图或用户继续操作
- **THEN** 系统不刷新权威业务活动时间

### Requirement: Warn and close idle interviews
系统 SHALL 在面试连续空闲 18 分钟时提示用户，并 MUST 在连续空闲 20 分钟且没有处理中任务时自动结束会话。

#### Scenario: User continues from warning
- **WHEN** 用户在自动结束前点击继续面试
- **THEN** 系统验证会话归属、刷新权威活动时间并关闭提示

#### Scenario: Session reaches idle timeout
- **WHEN** 会话连续 20 分钟没有有效业务活动且没有处理中任务
- **THEN** 系统将会话幂等更新为 `ended`、写入结束时间并在用户页面说明因空闲自动结束

#### Scenario: Answer is still processing
- **WHEN** 会话达到 20 分钟空闲阈值但存在仍在合理处理窗口内的回答或截图任务
- **THEN** 系统暂不结束会话，并在任务完成或保护窗口到期后重新判定

### Requirement: Release realtime resources on idle close
系统 MUST 在自动结束空闲面试时关闭实时发布通道、停止旧会话接收音频并释放设备绑定，且 SHALL 保留历史面试及账本记录。

#### Scenario: Desktop remains connected after timeout
- **WHEN** 面试已因空闲自动结束但桌面助手仍在运行
- **THEN** 旧会话绑定变为不可发布状态，助手可被后续新面试重新绑定

### Requirement: Enforce one active interview per user
系统 MUST 确保每个用户最多存在一条未删除且状态为 `live` 的面试会话，并 SHALL 对并发启动冲突返回可恢复结果。

#### Scenario: Concurrent starts race
- **WHEN** 同一用户并发启动两场面试
- **THEN** 数据库只允许一场进入 `live`，另一请求收到当前活跃面试信息且不得创建第二条活跃记录
