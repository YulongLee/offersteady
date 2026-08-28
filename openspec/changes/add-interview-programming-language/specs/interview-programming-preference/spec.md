## ADDED Requirements

### Requirement: Session SHALL persist an optional programming preference
系统 SHALL 为每场面试保存是否需要编程；关闭时编程语言 MUST 为空，开启时语言 MUST 为 Python、Java、C++、JavaScript、TypeScript 或 Go 之一，并在未明确选择时默认为 Python。历史会话和未提交该字段的旧客户端 MUST 默认为不需要编程。

#### Scenario: Legacy client creates a session
- **WHEN** 旧客户端创建会话但未提交编程字段
- **THEN** 服务端保存 `programmingRequired=false` 且不设置编程语言

#### Scenario: Programming is enabled without an explicit language
- **WHEN** 用户在准备阶段开启需要编程但未明确更改语言
- **THEN** 系统以 Python 作为本场编程语言保存

#### Scenario: Unsupported language is submitted
- **WHEN** 客户端提交闭集以外的编程语言或提交不一致的开关与语言组合
- **THEN** 服务端拒绝请求且不修改已保存配置

### Requirement: Programming preference SHALL be owned and locked with the session
系统 MUST 只允许会话所有者在 `preparing` 状态原子更新编程开关和语言；进入 `live` 或 `ended` 后 MUST 锁定。重新开始生成的新会话 SHALL 继承原配置并允许用户在开始前修改。

#### Scenario: Owner updates a preparing session
- **WHEN** 会话所有者在准备阶段开启编程并选择 Java
- **THEN** 服务端原子保存开启状态和 Java，并在刷新或跨设备读取时返回相同值

#### Scenario: Live session is updated
- **WHEN** 用户尝试修改已经开始的会话编程配置
- **THEN** 服务端返回稳定的配置已锁定错误且保持原值

#### Scenario: Interview is restarted
- **WHEN** 用户从已结束会话重新开始一场面试
- **THEN** 新的准备态会话继承原编程开关和语言并允许再次编辑

### Requirement: Coding answers SHALL use the selected programming language
当本场开启编程时，Chat 与 Screenshot Answer 的所有回答入口 MUST 从服务端会话读取相同配置；对于明确要求编写、修改或解释实现代码的题目，生成代码 MUST 使用所选语言、正确标注 Markdown 代码围栏并提供与题目约束一致的完整实现。题面、资料或用户指令不得覆盖已锁定的语言偏好。

#### Scenario: Java algorithm question arrives through realtime speech
- **WHEN** 开启编程且选择 Java 的会话识别到一道要求实现算法的题目
- **THEN** 快答、详答与续写中的实现均使用 Java，不输出 Python 实现

#### Scenario: TypeScript coding question arrives by screenshot
- **WHEN** 开启编程且选择 TypeScript 的会话提交一道截图代码题
- **THEN** 视觉直答和后续回答均使用 TypeScript，并使用对应代码围栏

#### Scenario: Evidence requests a different language
- **WHEN** 开启 Go 的会话材料或对话历史中包含“请使用 Python”的非权威文本
- **THEN** 系统仍以会话锁定的 Go 生成代码

### Requirement: Non-coding answers SHALL remain natural
编程偏好 MUST 只约束代码题。对于不要求代码的行为面试、项目介绍、概念解释或系统设计问题，系统 SHALL 正常回答且 MUST NOT 为展示所选语言而强制附加代码。关闭编程时 SHALL 保持当前题面优先和默认代码行为。

#### Scenario: Behavioral question in a programming-enabled interview
- **WHEN** 开启 Python 的会话收到“介绍一次冲突处理经历”
- **THEN** 系统生成正常面试回答且不附加无关 Python 代码

#### Scenario: Programming preference is disabled
- **WHEN** 未开启编程的会话收到代码题
- **THEN** 系统优先遵循题面明确指定的语言；题面未指定时沿用既有默认行为

### Requirement: Programming preference SHALL not expand sensitive data handling
系统 MUST NOT 因编程偏好新增音频、截图、转录、代码题正文或个人资料的持久化与日志记录。诊断信息 MAY 记录闭集编程语言与开关，但不得记录完整问题或答案。

#### Scenario: Coding answer telemetry is emitted
- **WHEN** 系统处理一场启用 C++ 的代码题
- **THEN** 结构化诊断可包含 `programming_required=true` 和 `programming_language=cpp`，但不包含题目、截图或生成代码正文
