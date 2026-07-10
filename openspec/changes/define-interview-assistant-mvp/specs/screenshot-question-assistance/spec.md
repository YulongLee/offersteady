## ADDED Requirements

### Requirement: Submit question screenshot
系统 MUST 允许用户通过文件选择、粘贴或受支持的截图入口提交题目图片，并在提交前说明截图的处理方式。

#### Scenario: Valid screenshot submitted
- **WHEN** 用户提交受支持且大小符合限制的图片
- **THEN** 系统显示预览并开始识别题目

#### Scenario: Invalid screenshot rejected
- **WHEN** 图片格式不受支持、超过限制或无法读取
- **THEN** 系统拒绝处理并提供可操作的修正说明

### Requirement: Extract and classify screenshot question
系统 SHALL 从截图中提取可检查的问题内容，并将问题分类为一般笔试题、代码题、系统设计题或未知类型。

#### Scenario: Question recognized
- **WHEN** 系统能够识别截图中的主要问题
- **THEN** 系统展示提取结果和题型，并允许用户修正后再生成回答

#### Scenario: Screenshot is ambiguous
- **WHEN** 图片模糊、内容不完整或无法确定主要问题
- **THEN** 系统说明无法可靠识别，并要求用户重新截图或补充文字

### Requirement: Generate type-appropriate response
系统 SHALL 根据题型生成适合的结构化回答，并在可用时结合简历、JD 和知识库上下文。

#### Scenario: System design question
- **WHEN** 问题被确认分类为系统设计题
- **THEN** 系统按需求澄清、规模估算、架构、数据模型、权衡和风险组织回答建议

#### Scenario: Coding question
- **WHEN** 问题被确认分类为代码题
- **THEN** 系统按思路、复杂度、边界情况和示例解法组织回答建议，并明确未实际执行的代码

#### Scenario: General written question
- **WHEN** 问题被确认为一般笔试题
- **THEN** 系统生成直接、结构化且标记依据的回答建议

### Requirement: Minimize screenshot retention
系统 MUST 默认只在完成当前识别和回答请求所需的时间内保留原始截图，除非用户明确选择保存。

#### Scenario: Screenshot response completes without save
- **WHEN** 回答完成且用户没有选择保存原图
- **THEN** 系统按短期处理策略清理原始截图，并只保留允许保留的题目文本和回答记录
