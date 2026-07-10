## ADDED Requirements

### Requirement: Remove the live material rail
实时面试页 MUST NOT 展示左侧面试资料栏、资料栏折叠按钮或现场“调整资料”入口。系统 MUST 继续让每条回答展示其生成时实际使用的来源，并 MUST 使用开始前已确认的资料选择版本处理新问题。

#### Scenario: Desktop live workspace opens
- **WHEN** 用户进入一场进行中的面试
- **THEN** 页面直接展示实时对话与回答工作区，不显示“面试资料”“收起资料”或“调整资料”侧栏控件

#### Scenario: Answer used selected sources
- **WHEN** 一条回答实际使用了简历、JD 或知识材料
- **THEN** 回答区域显示实际来源名称和版本，而无需常驻资料侧栏

#### Scenario: User wants to change materials
- **WHEN** 用户已经进入实时面试页
- **THEN** 页面不提供现场更换资料流程，用户结束或离开当前实时会话后才能在准备流程确认新的清单

### Requirement: Present conversation and answers as resizable desktop columns
在桌面视口中，实时工作台 MUST 将“实时对话”放在左栏、“回答”放在右栏，并 MUST 在两栏之间提供可拖动分隔条。拖动 SHALL 实时调整两栏比例，且任一栏不得小于保证核心内容可读和可操作的最小宽度。

#### Scenario: User opens the desktop workspace
- **WHEN** 视口达到桌面断点并加载实时面试页
- **THEN** 实时对话和回答以左右两栏出现，回答历史翻页和紧凑问题操作位于右侧回答栏

#### Scenario: User drags the divider
- **WHEN** 用户向左或向右拖动两栏之间的分隔条
- **THEN** 两栏宽度随指针移动并在达到任一最小宽度时停止继续压缩

#### Scenario: Streaming content updates during drag
- **WHEN** 用户调整分栏比例时对话修订或回答流式内容到达
- **THEN** 系统保持同一对话、答案、草稿和截图任务状态，不卸载或重复创建业务组件

### Requirement: Make the column divider accessible
分隔条 MUST 使用可识别的 separator 语义，MUST 暴露当前比例和允许范围，并 SHALL 支持键盘调整、焦点可见状态和恢复默认比例操作。分隔条不得成为访问对话、回答、历史翻页或面试操作的前置条件。

#### Scenario: Keyboard user adjusts the split
- **WHEN** 分隔条获得焦点且用户按左右方向键
- **THEN** 系统按固定步长改变两栏比例并更新可访问的当前值

#### Scenario: User restores the default split
- **WHEN** 用户在分隔条上执行恢复默认操作
- **THEN** 系统恢复产品定义的默认比例且两栏内容保持不变

#### Scenario: Pointer drag is unavailable
- **WHEN** 用户无法或不选择拖动分隔条
- **THEN** 默认布局仍能完整访问实时对话、回答和所有主要操作

### Requirement: Preserve a session-scoped split preference
系统 SHALL 在同一浏览器的当前面试会话中记住用户最后确认的桌面分栏比例，但 MUST NOT 将其作为跨账号服务端偏好。失效、超范围或旧版本的比例 MUST 回退到默认值。

#### Scenario: User returns to the same live session
- **WHEN** 用户调整比例后离开并在同一浏览器重新进入该场实时面试
- **THEN** 系统恢复该场会话保存的有效比例

#### Scenario: Stored ratio is invalid
- **WHEN** 本地保存值无法解析或不在允许范围内
- **THEN** 系统忽略该值并使用默认比例，不影响会话加载

### Requirement: Fall back to a single-column narrow layout
在平板和手机视口中，系统 MUST 移除可拖动分隔条并 SHALL 按“实时对话、回答、紧凑问题操作”的顺序单列展示。响应式切换 MUST NOT 丢失滚动中的内容、历史答案位置、手动问题草稿或截图任务。

#### Scenario: Viewport enters a narrow breakpoint
- **WHEN** 桌面实时页缩小到平板或手机断点
- **THEN** 两栏变为单列且不显示无效的拖动分隔条

#### Scenario: Viewport returns to desktop
- **WHEN** 视口从窄屏恢复到桌面断点
- **THEN** 系统恢复该场有效分栏比例并保留当前回答页和输入状态

#### Scenario: Phone keyboard opens
- **WHEN** 手机用户聚焦手动问题输入框
- **THEN** 回答问题和截图回答操作仍可滚动到可见区域且不被安全区遮挡
