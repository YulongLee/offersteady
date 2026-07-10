# Recent Interview Roster Maintenance Specification

## ADDED Requirements

### Requirement: Keep at most five recent interviews in the primary roster
首页最近面试区域 MUST 仅展示当前账号最近的 5 场可恢复或可复盘面试，并 SHALL 按最近活动时间倒序排列。系统 MUST NOT 在该主列表中无限追加更早的记录。

#### Scenario: User has fewer than five interviews
- **WHEN** 当前账号仅有 3 场面试记录
- **THEN** 最近面试列表展示这 3 场记录且不出现占位补齐项

#### Scenario: User has more than five interviews
- **WHEN** 当前账号已有 8 场面试记录
- **THEN** 最近面试列表仅展示最近活动时间最新的 5 场，其余记录不出现在首页主列表中

### Requirement: Allow users to delete recent interviews from the roster
最近面试中的每一场记录 MUST 提供明确删除入口。删除操作 MUST 经过确认，并以服务端确认结果为准；服务端未确认前，客户端不得仅本地隐藏该记录。

#### Scenario: User deletes a recent interview successfully
- **WHEN** 用户在最近面试列表中确认删除一场记录且服务端返回成功
- **THEN** 该记录从最近面试列表移除，剩余记录按最近活动时间重新补位

#### Scenario: Delete fails
- **WHEN** 用户确认删除后服务端返回失败
- **THEN** 该记录仍保留在列表中，系统展示可重试错误且不得宣称已删除

### Requirement: Creating a new interview keeps the roster within the five-item limit
创建新面试成功后，系统 MUST 将其插入最近面试列表顶部，并在总数超过 5 时移出最旧的一项可见记录，而不是阻止创建或要求用户先手动清理。

#### Scenario: New interview becomes the newest item
- **WHEN** 用户成功创建一场新面试
- **THEN** 该面试显示在最近面试列表首位

#### Scenario: New interview causes visible overflow
- **WHEN** 用户已有 5 场最近面试且成功创建第 6 场
- **THEN** 首页主列表仍只展示最新 5 场，原先最旧的可见项从首页主列表中移出
