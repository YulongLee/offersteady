## ADDED Requirements

### Requirement: Prioritize the answer on phones
手机端实时面试页 MUST 默认展示回答区域，并 MUST 通过“回答”和“对话”页签在有限视口内切换主内容。系统 MUST NOT 同时纵向堆叠完整对话、回答和操作区形成超长工作区。

#### Scenario: User opens a live interview on a phone
- **WHEN** 手机视口加载一场实时面试
- **THEN** “回答”页签默认激活且回答内容处于主可视区域

#### Scenario: User reviews the transcript
- **WHEN** 用户点击“对话”页签
- **THEN** 页面显示当前面试的实时对话且回答、草稿、历史位置与生成任务保持不变

### Requirement: Return to the answer when generation starts
手机端在快答、自动问题或截屏回答开始生成时 MUST 切换到回答页签，以便用户立即看到流式首段和最终答案。页签切换 MUST NOT 重复提交任务。

#### Scenario: User submits a manual question while reading conversation
- **WHEN** 用户位于“对话”页签并提交快答
- **THEN** 页面立即切换到“回答”页签且仅创建一个回答任务

#### Scenario: New answer arrives
- **WHEN** 后端同步到新的回答或活动回答任务
- **THEN** 手机端显示回答区域且保留稳定的答案历史 ID

### Requirement: Keep mobile actions reachable above the safe area
手机端 MUST 在底部安全区上方提供手动问题输入、快答和截屏回答操作，并 MUST 允许页面主内容独立滚动。软键盘或浏览器工具栏变化不得永久遮挡输入和主要操作。

#### Scenario: User focuses the question field
- **WHEN** 手机用户聚焦手动问题输入框
- **THEN** 输入框、快答和截屏回答仍可见或可在当前操作栏内访问

#### Scenario: Screenshot processing is active
- **WHEN** 截屏回答任务尚未完成
- **THEN** 截屏按钮被禁用并通过简短可访问状态反馈当前阶段

### Requirement: Keep the mobile header compact
手机端顶部 MUST 显示面试名称、收音状态和收音控制，结束面试等低频操作 SHALL 放入可访问的更多菜单。手机端 MUST NOT 再显示重复的底部“面试进行中”状态栏。

#### Scenario: Interview is capturing audio
- **WHEN** 手机端处于正在收音状态
- **THEN** 顶部提供可触摸的“暂停收音”控制且主内容获得更大可用高度

#### Scenario: User needs to finish the interview
- **WHEN** 用户打开顶部“更多”菜单
- **THEN** 菜单提供结束面试入口和账户/积分入口，而结束按钮不占用默认顶部宽度
