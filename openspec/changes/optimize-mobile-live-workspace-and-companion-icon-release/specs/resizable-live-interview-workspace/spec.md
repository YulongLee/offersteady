## MODIFIED Requirements

### Requirement: Fall back to a single-column narrow layout
在平板窄屏中，系统 MUST 移除可拖动分隔条并 SHALL 使用单列布局；在手机视口中，系统 MUST 使用“回答 / 对话”页签按需展示主区域，并 MUST 在底部安全区上方提供紧凑问题操作栏。响应式切换 MUST NOT 丢失历史答案位置、手动问题草稿、转录、活动回答或截图任务。

#### Scenario: Viewport enters a tablet breakpoint
- **WHEN** 桌面实时页缩小到平板但尚未进入手机断点
- **THEN** 两栏变为单列且不显示无效的拖动分隔条

#### Scenario: Viewport enters a phone breakpoint
- **WHEN** 视口进入手机断点
- **THEN** 页面默认展示回答页签，可切换到实时对话，并在安全区上方显示输入、快答和截屏回答

#### Scenario: Viewport returns to desktop
- **WHEN** 视口从窄屏恢复到桌面断点
- **THEN** 系统恢复该场有效分栏比例并保留当前回答页、输入草稿和任务状态

#### Scenario: Phone keyboard opens
- **WHEN** 手机用户聚焦手动问题输入框
- **THEN** 输入、快答和截图回答操作保持可访问且不被安全区永久遮挡
