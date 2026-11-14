## ADDED Requirements

### Requirement: Mobile transcript touch scrolling reaches the complete conversation
手机实时面试的对话页签 MUST 支持从对话文字上发起的纵向触摸滚动，并 MUST 能查看完整长对话。对话列表 MUST 具有受可用视口约束的滚动范围，保留现有手动回看及跟随最新转写行为。

#### Scenario: User swipes within a long conversation
- **WHEN** 手机用户在超出一屏的对话文字上向上滑动
- **THEN** 对话列表向下滚动，后续段落可见且底部操作仍可访问

#### Scenario: User reviews an earlier turn
- **WHEN** 手机用户滑回较早对话且此时新增转写
- **THEN** 当前回看位置不被自动拉回末尾

### Requirement: Mobile answer and mock interview content remain reachable
修复 MUST 保留手机长回答的连续滚动，且模拟面试准备、作答和报告页 MUST 可滚动至末尾及主要操作。测试 MUST 使用合成数据，不创建真实面试或调用模型。

#### Scenario: User reads a long answer
- **WHEN** 手机回答内容超出一屏
- **THEN** 从回答正文发起滑动能够到达完整回答末尾

#### Scenario: User accesses mock interview actions and report
- **WHEN** 手机模拟面试准备、作答或报告内容超出一屏
- **THEN** 用户能够滑动至页面末尾及相应操作
