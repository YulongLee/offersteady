## Why

用户在创建面试时已经导入或选择资料，但实时问答没有稳定按照这些资料回答，说明资料库、会话资料快照、RAG 检索和回答 Prompt 之间仍缺少可观测、可验证的闭环。现在需要把“资料是否被选中、是否进入本场、是否进入模型上下文、回答是否使用资料”这几个事实串起来，避免用户以为资料已生效而 AI 实际在泛答。

## What Changes

- 明确资料进入面试的准入规则：只有后端确认可用的简历、JD 和知识库资料才能被确认到本场面试。
- 明确资料在回答中的使用边界：简历和 JD 作为本场固定上下文进入 Prompt；知识库通过 RAG 检索和 rerank 进入上下文。
- 增加回答前的资料上下文装配校验：如果用户选择了资料但后端无法读取、检索或注入，回答任务必须记录可见原因，不能静默退化为泛答。
- 增加回答结果的安全来源说明：展示本次回答是否使用了简历、JD、知识库片段及其版本，避免只看 `retrievalCount` 误判简历/JD 未使用。
- 增加无匹配资料或资料不可用时的回答约束：必须明确说明未使用到个人资料，不得编造候选人的公司、项目、职责或指标。
- 增加针对创建面试导入资料后的端到端验证场景：上传/选择资料、确认本场、提问、检查 prompt context/RAG/provenance。
- 不改变现有页面原型结构，不新增复杂资料编辑器，不引入客户端密钥或浏览器直连模型能力。

## Capabilities

### New Capabilities
- `material-grounded-interview-answering`: 资料进入面试后的端到端 grounding 行为，包括固定资料上下文、知识库 RAG、回答来源说明和退化提示。

### Modified Capabilities
- `streamlined-interview-entry`: 准备页确认资料时必须展示并保存资料可用性、选择快照和后端确认结果，避免不可用资料被带入本场面试。

## Impact

- `apps/backend`: Session Service、Chat Service、Screenshot Answer Service、Retrieval Service、Document/Material availability 校验、回答任务响应 payload 和日志。
- `apps/web`: 创建面试/准备页资料选择状态、实时回答来源展示、资料不可用提示和回答退化提示，不改变当前页面布局。
- `packages/protocol`: 会话资料快照、回答 provenance、资料上下文装配状态和不可用原因字段。
- `ai/prompts`: 明确简历/JD 固定上下文、知识库 RAG 上下文和无资料时的回答约束。
- `ai/evals`: 增加“已选择简历/JD/知识库后必须引用资料事实”和“无资料不得编造经历”的评测案例。
- 隐私影响：回答 provenance 只展示来源名称、类型、版本和短摘要，不暴露原始全文、完整 Prompt、embedding 或供应商 payload。
