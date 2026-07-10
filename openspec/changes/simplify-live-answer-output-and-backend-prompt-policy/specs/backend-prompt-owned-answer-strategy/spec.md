# Backend Prompt Owned Answer Strategy Specification

## ADDED Requirements

### Requirement: The backend MUST own answer organization strategy
系统 MUST 由后端 Prompt Template、Prompt Builder 和 Chat Service 统一决定回答的组织方式、表达风格、详略程度与现场回答策略。前端 MUST NOT 依赖固定的展示提纲结构来补足回答策略。

#### Scenario: Prompt strategy changes
- **WHEN** 产品希望把回答风格从“提纲式”调整为“直接可说出口的正文式”
- **THEN** 系统可以通过后端 prompt 配置完成调整，而不要求前端重写回答结构逻辑

#### Scenario: Frontend renders a completed manual answer
- **WHEN** 后端返回一条已完成的实时回答
- **THEN** 前端以返回的主回答正文作为首要内容渲染，而不是假设必须存在固定 outline/inference 结构

### Requirement: The frontend MUST treat answer text as the primary output
实时面试页在展示已完成回答时 SHALL 以模型返回的主回答正文为第一视觉层。前端可以保留生成状态、失败状态、历史翻页和最小化来源信息，但 MUST NOT 让固定解释卡片压过回答正文本身。

#### Scenario: User asks a direct interview question
- **WHEN** 用户点击“快答”并收到模型回答
- **THEN** 回答区首先显示完整回答正文，用户无需先展开“回答思路”或跨越多个解释模块

#### Scenario: Answer generation fails
- **WHEN** 后端返回失败状态
- **THEN** 前端仍展示失败原因与恢复入口，但不会用占位提纲伪装成可用回答
