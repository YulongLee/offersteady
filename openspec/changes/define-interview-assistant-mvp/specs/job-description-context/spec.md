## ADDED Requirements

### Requirement: Upload job description
系统 MUST 允许用户通过文件上传或文本粘贴添加目标岗位 JD。

#### Scenario: JD text submitted
- **WHEN** 用户粘贴非空 JD 文本并确认
- **THEN** 系统保存待解析内容并显示处理状态

#### Scenario: JD file submitted
- **WHEN** 用户上传受支持的 JD 文件
- **THEN** 系统接受文件并开始解析

### Requirement: Extract job requirements
系统 SHALL 从 JD 中提取岗位职责、必备技能、加分项和业务背景，并允许用户检查和修改解析结果。

#### Scenario: JD parsing succeeds
- **WHEN** JD 解析完成
- **THEN** 系统展示分类后的岗位要求并标记解析完成

#### Scenario: JD lacks useful detail
- **WHEN** 输入内容不足以识别岗位要求
- **THEN** 系统提示用户补充信息且不把推测内容标记为原始 JD

### Requirement: Align answers with JD
系统 SHALL 在生成回答建议时使用与当前问题相关的岗位要求，并明确区分 JD 原文与 AI 推断。

#### Scenario: Question maps to a job requirement
- **WHEN** 当前问题与某项已确认岗位要求相关
- **THEN** 系统在回答中突出与该要求匹配的候选人经历或知识

### Requirement: Replace or delete JD
系统 MUST 允许用户替换或删除当前 JD 及其派生内容。

#### Scenario: User replaces JD
- **WHEN** 用户确认使用新 JD 替换旧 JD
- **THEN** 系统停止使用旧 JD，重新解析新内容并更新回答上下文
