## ADDED Requirements

### Requirement: Omit the live material rail
实时工作台 MUST NOT 展示本场资料辅助栏、折叠操作或现场调整资料入口。回答区 MUST 继续显示每条回答实际使用的资料来源和选择版本。

#### Scenario: User opens the live workspace
- **WHEN** 用户进入一场进行中的面试
- **THEN** 页面直接展示实时对话与回答，且不存在“面试资料”“收起资料”“展开资料”或“调整资料”控件

#### Scenario: Answer uses a prepared source
- **WHEN** 回答实际使用了开始前确认的资料
- **THEN** 回答区域显示该来源名称、版本和选择 revision

### Requirement: Use a two-region main workspace
实时工作台 MUST 将主内容简化为“实时对话”和“回答”两个清晰区域。桌面端 MUST 以可调整宽度的左右两栏展示，窄屏 MUST 降级为上下单列。设备状态 SHALL 以紧凑状态展示，转录和历史答案 MUST 分别进入对应主区域。

#### Scenario: User opens the desktop live workspace
- **WHEN** 桌面视口加载一场进行中的面试
- **THEN** 左栏显示实时对话，右栏显示回答、历史翻页和紧凑输入栏，页面不存在资料或历史/设备侧栏

#### Scenario: User adjusts the divider
- **WHEN** 用户通过指针或键盘调整两栏之间的分隔条
- **THEN** 两栏在最小宽度范围内改变比例且对话、回答和输入状态保持不变

### Requirement: Present the live conversation chronologically
实时对话区 SHALL 按时间顺序展示“面试官”与“我”的转录片段，并 MUST 显示时间、临时/最终状态和必要的文本不确定性。角色 MUST 由双声道来源确定，相同片段的流式修订 MUST 更新原位置而不是新增重复对话。

#### Scenario: Interviewer and candidate alternate speaking
- **WHEN** 系统收到双方带角色和时间的转录片段
- **THEN** 对话区按时间显示“面试官”和“我”，并以文字区分最终转录与转写中状态

#### Scenario: Interim transcript is revised
- **WHEN** 同一片段 ID 收到更高 revision 的文本
- **THEN** 系统原位更新该片段且保持用户当前阅读位置

### Requirement: Answer interviewer questions by default
回答系统 MUST 只自动处理系统音频中已确认的面试官问题；本地麦克风中的陈述、回答、寒暄或重复转录 MUST NOT 自动创建新答案。文本或边界低置信度问题 SHALL 在实时对话区提供确认或忽略操作，角色不提供待确认状态。

#### Scenario: Confirmed interviewer question arrives
- **WHEN** 系统音频最终转录被确认为完整面试官问题
- **THEN** 系统创建一次回答任务并把新答案设为最新答案

#### Scenario: Candidate is answering
- **WHEN** 最终转录片段的角色为面试者
- **THEN** 对话区继续显示该片段，但系统不创建回答任务或计费用量

#### Scenario: Transcript confidence is insufficient
- **WHEN** 一条系统音频问题的文本或边界未达到自动确认阈值
- **THEN** 对话区显示“确认问题”和“忽略”，确认后才创建唯一回答任务

### Requirement: Page through answers inside the answer region
回答区 SHALL 在同一区域展示最新答案和历史答案，并 MUST 提供上一条、下一条、当前位置和“回到最新”操作。历史翻页 MUST 使用稳定答案 ID，不得因新答案插入而跳到另一条历史记录。

#### Scenario: User browses an older answer
- **WHEN** 用户从最新答案点击“上一条”
- **THEN** 回答区展示前一条答案、显示其原问题和来源，并更新当前位置而不打开侧栏

#### Scenario: New answer arrives while history is open
- **WHEN** 用户正在查看旧答案且系统生成一条新答案
- **THEN** 系统保留当前历史页、显示“有新答案”提示，并提供“回到最新”操作

#### Scenario: User reaches a history boundary
- **WHEN** 用户位于第一条或最后一条可浏览答案
- **THEN** 对应翻页按钮被禁用并提供可理解的禁用状态

### Requirement: Provide a compact dual-action input bar
系统 SHALL 在主区底部提供紧凑的手动问题输入栏，并 MUST 在输入框旁提供“回答问题”和“截图回答”两个按钮。按钮不得使用大面积卡片样式，也不得在按钮或输入栏中显示点数。

#### Scenario: User submits a manual question
- **WHEN** 用户输入非空问题并点击“回答问题”
- **THEN** 系统通过同一幂等回答管线提交问题、清空已成功提交的输入并展示最新答案状态

#### Scenario: Manual question is empty
- **WHEN** 输入框为空或只有空白字符
- **THEN** “回答问题”按钮保持禁用并说明需要先输入问题

#### Scenario: User starts a screenshot answer
- **WHEN** 用户点击“截图回答”
- **THEN** 系统进入截图选择或预览流程，输入框草稿和当前答案页保持不变

### Requirement: Keep live controls free of point labels
实时工作台的手动回答、自动回答和截图入口 MUST NOT 展示单次点数或会员价格文案。服务端费率、余额校验、幂等预留、结算与释放规则 MUST 保持有效，积分页面 SHALL 继续展示费率和明细。

#### Scenario: User has sufficient entitlement
- **WHEN** 用户提交问题且服务端确认余额或会员权益可用
- **THEN** 系统创建回答任务，实时操作区不插入点数标签

#### Scenario: User lacks sufficient balance
- **WHEN** 服务端拒绝回答任务因为余额不足
- **THEN** 实时页显示余额不足和前往积分页的恢复入口，不得把任务显示为生成中或成功

#### Scenario: Screenshot processing fails
- **WHEN** 截图识别或回答生成失败
- **THEN** 系统显示失败与重试状态并释放预留，实时按钮仍不显示点数

### Requirement: Adapt the focused workspace accessibly
系统 MUST 在平板和手机继续使用实时对话、回答和紧凑输入栏的相同信息顺序，并 MUST 移除桌面分隔条。翻页、回答问题和截图回答必须支持键盘、触摸与可访问名称，且不得被软键盘、安全区或会话控件遮挡。

#### Scenario: User opens the workspace on a phone
- **WHEN** 视口进入手机断点
- **THEN** 页面按实时对话、回答、紧凑输入栏顺序显示，且不存在资料抽屉或右侧栏

#### Scenario: On-screen keyboard opens
- **WHEN** 用户聚焦手动问题输入框
- **THEN** 输入内容和两个操作按钮仍可滚动或调整到可见区域

### Requirement: Protect sensitive live content
系统 MUST 对实时转录、问题和答案保持会话访问控制与最小化日志，并 MUST 避免将完整对话或回答暴露到页面标题、系统通知或未授权设备。

#### Scenario: Unauthorized device requests the live workspace
- **WHEN** 未授权设备请求一场进行中的面试
- **THEN** 系统拒绝返回资料、对话、问题、历史答案和设备详情
