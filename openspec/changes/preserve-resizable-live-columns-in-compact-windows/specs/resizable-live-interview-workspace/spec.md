## MODIFIED Requirements

### Requirement: Present conversation and answers as resizable desktop columns

在桌面和平板尺寸窗口中，实时工作台 MUST 将“实时对话”放在左栏、“回答”放在右栏，并 MUST 保留可拖动及键盘可操作的分隔条。窗口缩小但仍大于手机断点时，系统 MUST 使用紧凑最小宽度继续提供分栏调整，而不是提前切换为上下布局。

#### Scenario: User narrows a desktop interview window

- **WHEN** 实时面试窗口缩小到 721px 至 1050px
- **THEN** 实时对话和回答仍以左右两栏显示
- **AND** 中间分隔条仍可拖动或使用键盘调整

#### Scenario: Compact window reaches a readable bound

- **WHEN** 用户在紧凑窗口中拖动分隔条接近任一侧
- **THEN** 系统按紧凑窗口最小宽度限制比例
- **AND** 两侧核心内容与操作仍保持可读可用

### Requirement: Fall back to a single-column narrow layout

系统 MUST 仅在手机尺寸视口中移除分隔条并切换为上下单列布局。响应式切换 MUST NOT 丢失对话、答案、草稿或截图任务状态。

#### Scenario: Viewport reaches the phone breakpoint

- **WHEN** 实时面试视口缩小到 720px 或以下
- **THEN** 页面按既有顺序切换为单列
- **AND** 不显示对手机无效的拖动分隔条

#### Scenario: Viewport returns above the phone breakpoint

- **WHEN** 视口重新扩大到 721px 或以上
- **THEN** 页面恢复左右分栏和该场有效比例
- **AND** 当前回答页与输入状态保持不变
