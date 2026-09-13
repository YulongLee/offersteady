## ADDED Requirements

### Requirement: Load independent versioned prompts per locale and stage
系统 MUST 为每个 production locale 提供独立、版本化的 system、quick、detail、continuation 和 screenshot 提示词资源；运行时 MUST 根据权威 session locale 加载资源，禁止使用机器翻译或跨语言静默回退。

#### Scenario: French quick answer
- **WHEN** 法语会话请求快答
- **THEN** Chat Service 加载法语 quick 资源，返回法语结构化回答并记录模板 ID/version

#### Scenario: Missing beta asset
- **WHEN** Beta 语言缺少某个阶段资源
- **THEN** 该阶段以可恢复错误结束，不加载中文或英文模板

### Requirement: Apply a commercial interview answer contract
每套语言提示词 MUST 要求专业、自然、适合面试口述的商业化表达：先给结论，再给证据/方法/结果；只使用可验证的简历、JD、知识库和截图事实；区分事实、推断和建议；不得虚构候选人经历；代码题遵守选定编程语言和约束；输出必须标记为 AI 建议。

#### Scenario: Answer grounded in Chinese material
- **WHEN** 英语或日语会话使用中文简历作为证据
- **THEN** 模型以会话语言表达可验证事实，保留事实含义，不把中文资料原文当作输出语言要求

#### Scenario: Unsupported claim appears in evidence
- **WHEN** 资料无法证明某个项目指标
- **THEN** 回答明确标记不确定性或要求用户补充，不编造指标

### Requirement: Keep stage labels and language validation consistent
快答、详答、续写、截图回答和安全回退 MUST 使用会话语言的可见标签；语言检测失败或 provider 返回明显错误语言时 MUST 进行有限修复尝试，仍失败则不发布为成功答案。

#### Scenario: Provider drifts to another language
- **WHEN** 德语会话的 provider 返回一段明显英语答案
- **THEN** 系统执行一次有界语言修复；若仍不符合德语契约，则以无内容错误结束并保留可重试操作
