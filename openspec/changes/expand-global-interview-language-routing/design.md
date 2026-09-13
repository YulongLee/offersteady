## Context

`apps/web-global` 已有 `zh-CN | en-US` 的会话语言字段、准备页控件和后端路由，但 Global 产品目前把新会话固定为 `en-US`，用户设置也没有默认面试语言。ASR 供应商可以识别约 30 种语言，而回答模型没有公开严格语言白名单；因此本变更必须把“供应商可识别”与“产品可承诺”分开，并保证语言在一次会话的所有阶段保持一致。

本设计保留现有深色商业化视觉和页面网格，只扩展现有语言选择控件、设置项、徽标和错误状态。简历、JD、音频、截图和知识材料仍是敏感数据，不增加持久化范围。

## Goals / Non-Goals

**Goals:**

- 支持会话级语言选择、用户默认语言、刷新恢复和开始后锁定。
- 让 ASR、问题检测、所有回答阶段、截图、复盘和导出使用同一权威语言。
- 将首批生产语言和实验语言显式区分，避免对未经验证的模型能力作商业承诺。
- 为每种启用语言维护独立、版本化、可评测的提示词，遵守事实来源、候选人真实经历和建议性质约束。

**Non-Goals:**

- 不重做首页布局或引入整站翻译框架。
- 不在一场面试中自动切换语言、不做逐句混合语言路由。
- 不把运行时机器翻译当作提示词资源，不翻译或覆盖用户资料原文。
- 不更换 ASR/LLM 供应商，不把密钥放到客户端。

## Decisions

### 1. Use an explicit locale registry with release tiers

在共享协议中定义稳定 locale registry，覆盖 ASR 已声明的语言：`zh-CN`、`en-US`、`ja-JP`、`ko-KR`、`vi-VN`、`th-TH`、`id-ID`、`ms-MY`、`fil-PH`、`hi-IN`、`ar-SA`、`fr-FR`、`de-DE`、`es-ES`、`pt-BR`、`ru-RU`、`it-IT`、`nl-NL`、`sv-SE`、`da-DK`、`fi-FI`、`nb-NO`、`el-GR`、`pl-PL`、`cs-CZ`、`hu-HU`、`ro-RO`、`bg-BG`、`hr-HR`、`sk-SK`。

每个条目包含显示名称、ASR provider code、回答输出标签、RTL 标记和 `production | beta` release tier。首批 production tier 为中文、英语、日语、韩语、法语、德语、西班牙语、葡萄牙语、意大利语和俄语；其余语言先作为 beta，只有在对应 ASR/回答评测和人工验收通过后才可在生产默认展示。这样既满足完整链路建模，也避免把模型未验证的语言质量误写成产品保证。

备选方案是只保留英文并在界面写“支持多语言”，但无法满足用户选择语言的需求；另一方案是允许任意 BCP-47 字符串，会导致供应商语言码、提示词和测试不可控，因此不采用。

### 2. Keep session locale authoritative and user preference separate

在用户设置增加 `defaultInterviewLanguage`，在创建草稿时作为默认值；准备页允许对当前草稿覆盖并通过所有权校验 API 保存。`interviewLanguage` 在会话开始后不可变，历史会话按原值恢复，旧客户端缺失字段时仍使用 `zh-CN` 或 Global 既有 `en-US` 兼容值。任何音频、手动问题或截图请求都不能携带覆盖语言。

### 3. Route provider adapters through a locale capability map

后端新增 `InterviewLocaleDefinition`/registry，将产品 locale 映射到 ASR provider code、prompt 目录和输出检测规则。ASR 连接、预热、重连和缓存键均使用 locale；Chat、Screenshot 和问题规范化入口只从权威 session 读取 locale。供应商不可用、语言码不支持或语言资源缺失时返回稳定的可恢复错误，不静默回退为中文或英文。

### 4. Version prompts by locale and business stage

在 `ai/prompts/` 下按 locale/stage 管理 `system`、`quick`、`detail`、`continuation`、`screenshot` 资源。每套资源都明确：输出语言、商务面试语气、先结论后证据、只使用简历/JD/知识库中可验证事实、标记推断、不虚构经历、代码题遵守选定编程语言，以及 AI 输出仅为建议。中文和现有英文资源保持行为兼容；新语言先复用同一结构但必须有人工审阅版本，禁止运行时翻译。

### 5. Make UI language changes additive

沿用现有 `.interview-language-picker`、设置面板和 `live-language-badge` 样式，将语言列表放入原生可访问的折叠面板。准备页默认以紧凑摘要显示当前语言（新会话默认为英语），通过明确的展开操作查看和切换其他语言；默认布局、颜色、间距和主要 CTA 不变。英语摘要与条目使用绿色的默认 Production 标识，其他条目显示“生产支持”或“Beta”标签；RTL 语言只增加方向属性和文本流适配，不重排页面结构。

### 6. Gate commercial claims with evals and telemetry

每种 locale 必须有合成 ASR、问题规范化、快答/详答/续写、截图和中文资料 grounding 案例；评测未通过的语言保持 beta 或隐藏。遥测只写 locale、tier、stage、模板 ID/version、延迟、错误类别和 token 统计，不写音频、截图、转录、简历或完整回答。

## Risks / Trade-offs

- [ASR 支持不等于回答模型稳定支持] → locale registry 分 release tier；没有完整评测的语言不能标为 production。
- [30 种语言的提示词维护成本高] → 先建立统一商业回答结构和首批十种生产资源，其余按同一契约逐批开放。
- [部分语言需要 RTL 或不同标点/分段规则] → 在 locale 定义中保存方向和格式化规则，UI 仅做增量适配。
- [语言选择增加准备页决策负担] → 使用现有卡片控件，记忆用户默认值，并保持 readiness 计算不变。
- [资源缺失导致用户无法开始] → 发布前启动检查所有 production 资源；运行时 fail closed 并提供切换到已验证语言的恢复操作。

## Migration Plan

1. 增加 locale registry、用户默认设置字段和向后兼容迁移；旧会话保持原语言。
2. 部署后端语言映射、适配器和 production prompt 资源，运行多语言合成评测。
3. 部署 Web 设置项和准备页选择；默认仍为当前版本语言，beta 语言默认不参与新用户自动选择。
4. 对内部账号开放 beta 语言，收集仅含语言维度的质量/延迟指标，通过门禁后再提升为 production。
5. 回滚时隐藏新语言并停止创建对应会话；已开始会话继续使用其已锁定语言，数据库字段保留。

## Open Questions

- 是否在首个版本直接向所有用户展示 30 种语言，还是先只展示十种 production 语言、其余通过 Beta 开关开放？本设计默认后者。
- 各市场的默认语言和商务语气（美式/英式、正式程度）是否需要按区域进一步拆分？
