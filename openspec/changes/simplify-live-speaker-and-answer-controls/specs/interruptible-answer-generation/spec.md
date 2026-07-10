## ADDED Requirements

### Requirement: Offer a stop control while an answer is being generated
回答区域 MUST 在最新回答处于排队或生成状态时提供紧凑且可访问的“终止回答”操作。回答已经完成、失败或终止后 MUST 隐藏或禁用该操作，且历史答案翻页不得错误控制另一条任务。

#### Scenario: Latest answer is streaming
- **WHEN** 用户正在查看一条仍在生成的最新回答
- **THEN** 回答区域显示“终止回答”操作并通过可访问名称说明其作用

#### Scenario: User is reading a historical answer
- **WHEN** 用户翻页查看非最新历史答案而后台有新回答生成
- **THEN** 历史答案内容不出现会误终止该历史记录的操作，页面仍以明确方式提供当前生成任务控制

#### Scenario: Answer is no longer cancellable
- **WHEN** 回答已经完成、失败或终止
- **THEN** 页面不再把该回答展示为可终止状态

### Requirement: Cancel answer generation through an idempotent server command
系统 MUST 使用当前用户、面试会话、回答任务 ID 和期望版本发送幂等终止命令。服务端 SHALL 尝试取消可替换模型适配器的上游请求，并 MUST 将已接受终止后的迟到分片和完成事件隔离，避免恢复已终止回答。

#### Scenario: User stops an active answer
- **WHEN** 服务端接受一条仍在排队或生成任务的终止命令
- **THEN** 任务进入 `cancelled` 最终状态、停止发布新内容并向所有已授权 Web 客户端同步“已终止”

#### Scenario: Stop command is repeated
- **WHEN** 同一回答任务的终止命令因重试被重复提交
- **THEN** 服务端返回相同最终结果且不重复释放资源、积分或生成新的状态事件

#### Scenario: Provider sends a late chunk
- **WHEN** 上游模型在终止已被接受后仍发送内容分片或完成回调
- **THEN** 服务端丢弃迟到内容并保持任务为 `cancelled`

### Requirement: Keep interview capture independent from answer cancellation
终止回答 MUST NOT 暂停、停止或重新授权当前面试的音频采集，也 MUST NOT 清空实时对话、手动问题草稿、截图任务或其他历史答案。后续面试官问题仍 SHALL 按正常规则创建新的回答。

#### Scenario: User stops an unwanted answer
- **WHEN** 用户终止当前回答后面试仍在进行
- **THEN** 音频采集和实时转录保持原状态，下一条有效面试官问题仍可触发新回答

#### Scenario: User wants to answer the same question again
- **WHEN** 用户对已终止问题执行重新回答
- **THEN** 系统创建新的回答任务并保留前一任务的已终止审计状态，不在原任务上恢复流式输出

### Requirement: Settle usage from the authoritative cancellation outcome
回答计费 MUST 以服务端最终任务状态为准。成功终止且未形成可用结果的任务 MUST 释放积分预留且不得结算回答点数；若完成事件先于终止命令成为最终状态，系统 SHALL 保留完成结果并按既有成功规则结算，不得向用户宣称已经终止。

#### Scenario: Cancellation wins before completion
- **WHEN** 终止命令先被服务端接受且任务最终为 `cancelled`
- **THEN** 系统释放该任务的积分预留、记录零结算并显示“回答已终止”

#### Scenario: Completion wins the race
- **WHEN** 回答已经原子完成后服务端才处理终止命令
- **THEN** 服务端返回不可终止结果，Web 保留完整回答并按成功结果结算一次

#### Scenario: User has an unlimited pass
- **WHEN** 会员用户终止回答
- **THEN** 系统仍记录任务取消结果与用量事件，但不创建积分扣减或重复权益消耗

### Requirement: Preserve partial text without presenting it as usable advice
终止前已显示的临时分片 SHALL 从主要回答建议中停止增长，并 MUST 明确标记为未完成。系统不得把未完成分片计入可用回答、复盘建议或 AI 质量成功指标；可按最小审计策略保留任务状态而不保留完整临时正文。

#### Scenario: User stops after partial text appears
- **WHEN** 回答已经显示部分流式文字后被成功终止
- **THEN** 页面以“回答已终止”取代生成状态，不把部分文字标记为完整回答建议或依据充足
