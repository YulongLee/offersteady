# Resizable Live Interview Workspace Specification Delta

## MODIFIED Requirements

### Requirement: Desktop live workspace keeps conversation and answer as the two primary columns
在桌面视口中，右侧回答区 MUST 以当前问题对应的模型回答正文为主要阅读内容。系统 MAY 显示最小化的回答依据、版本或状态信息，但 MUST NOT 要求用户先阅读固定提纲、推断说明或展开卡片才能获得主要回答。

#### Scenario: Completed answer is shown on desktop
- **WHEN** 用户在实时面试页收到一条完成的回答
- **THEN** 右侧回答区直接展示该回答正文，并把状态、来源和辅助信息放在次级位置

#### Scenario: User flips through answer history
- **WHEN** 用户查看历史回答
- **THEN** 每一条历史记录也以回答正文为主要内容展示，而不是继续强制使用多层建议卡片结构
