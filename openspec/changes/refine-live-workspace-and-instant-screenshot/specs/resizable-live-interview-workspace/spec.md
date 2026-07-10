## MODIFIED Requirements

### Requirement: Present conversation and answers as resizable desktop columns
在桌面视口中，实时工作台 MUST 将“实时对话”放在左栏、“回答”放在右栏，并 MUST 在两栏之间提供可拖动分隔条。左栏 MUST 在实时对话区域下方承载手动问题输入框，右栏 MUST 在回答区域下方承载“快答”和“截屏回答”两个紧凑操作块。会话级“开始面试”和“结束面试”控制 MUST 固定在页面右上角头部区域，而不是占用页面底部主操作位。拖动 SHALL 实时调整两栏比例，且任一栏不得小于保证核心内容可读和可操作的最小宽度。

#### Scenario: User opens the desktop workspace
- **WHEN** 视口达到桌面断点并加载实时面试页
- **THEN** 左栏显示实时对话及其下方的手动问题输入框，右栏显示回答及其下方的“快答”和“截屏回答”操作，右上角显示“开始面试”和“结束面试”控制

#### Scenario: User drags the divider
- **WHEN** 用户向左或向右拖动两栏之间的分隔条
- **THEN** 两栏宽度随指针移动并在达到任一最小宽度时停止继续压缩，且左侧输入框草稿、右侧当前答案与操作状态保持不变

#### Scenario: Streaming content updates during drag
- **WHEN** 用户调整分栏比例时对话修订或回答流式内容到达
- **THEN** 系统保持同一对话、答案、左侧输入草稿和右侧动作状态，不卸载或重复创建业务组件

### Requirement: Fall back to a single-column narrow layout
在平板和手机视口中，系统 MUST 移除可拖动分隔条，并 SHALL 按“实时对话、手动问题输入、回答、快答/截屏回答”的顺序单列展示。响应式切换 MUST NOT 丢失滚动中的内容、历史答案位置、手动问题草稿或截图任务。

#### Scenario: Viewport enters a narrow breakpoint
- **WHEN** 桌面实时页缩小到平板或手机断点
- **THEN** 两栏变为单列且不显示无效的拖动分隔条，页面依次展示实时对话、手动问题输入、回答和快答/截屏回答

#### Scenario: Viewport returns to desktop
- **WHEN** 视口从窄屏恢复到桌面断点
- **THEN** 系统恢复该场有效分栏比例，并继续保留当前回答页、手动问题草稿和截图状态

#### Scenario: Phone keyboard opens
- **WHEN** 手机用户聚焦手动问题输入框
- **THEN** 输入内容、回答区域以及快答/截屏回答操作仍可滚动到可见区域且不被安全区遮挡
