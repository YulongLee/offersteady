## Context

面试语言已经是服务端会话的权威配置，并由准备页保存、刷新恢复和开始后锁定。编程偏好具有相同生命周期，但它只影响代码题的生成语言，不影响 ASR、界面语言或非代码题。当前 Chat 和 Screenshot Answer 都从会话读取配置并构建 Prompt，截图直连视觉模型另有一条 Prompt 入口，因此必须覆盖两条回答链路。

## Goals / Non-Goals

**Goals:**

- 提供默认关闭、开启后默认 Python 的会话级编程偏好。
- 在实时文字/语音问题和截图代码题中稳定使用所选语言。
- 让历史会话、旧客户端、刷新、跨设备和重新开始具备确定的兼容行为。
- 将 AI 行为约束集中在 Prompt 资产中，并以合成测试和 eval 验证。

**Non-Goals:**

- 不做在线 IDE、代码执行、编译、判题或代码格式化器。
- 不自动猜测用户偏好的语言，也不支持每道题临时切换语言。
- 不把所有技术问答强制改成代码答案；只有明确代码/算法实现请求才受约束。
- 不改变现有面试语言、音频、截图上传、计费和资料保存规则。

## Decisions

### 1. Store a closed programming preference on the authoritative session

会话增加 `programming_required` 布尔值和 `programming_language` 闭集字段。首期语言枚举为 `python | java | cpp | javascript | typescript | go`。关闭时服务端规范化为 `programming_language=null`；开启但旧客户端未提供语言时使用 `python`。历史数据迁移为关闭状态。

该配置只允许会话所有者在 `preparing` 状态更新，开始后锁定；重新开始会继承原值并重新允许编辑。选择服务端持久化而不是 localStorage，可保证自动问题、手动问题、截图和跨设备读取同一事实。

### 2. Use one atomic update command for the switch and language

提供单个编程偏好更新 API，同时提交 `programmingRequired` 与 `programmingLanguage`，避免先开开关再保存语言形成无效中间状态。Web 仅在开启时展示语言选择器，默认选择 Python；保存失败时继续显示服务端最后确认值。该配置有效默认值始终存在，因此不增加开始面试门禁。

备选方案是复用面试语言 API，但两个配置的语义、枚举与错误码不同，拆分命令更易校验和演进。

### 3. Render a centralized programming policy into every answer Prompt

在 `ai/prompts/` 增加中英文可版本化的编程策略模板。服务层根据权威会话配置渲染只包含闭集显示名的结构化策略块，并传给 Chat 的 quick/detail/continuation/legacy 路径和 Screenshot 的视觉直答/二阶段回答路径。策略要求：题目明确要求代码时使用所选语言、代码围栏标注对应语言、给出完整可运行实现；非代码题正常作答，不为了展示语言而强加代码。

不把用户可控字符串直接拼接为 Prompt，也不把整段规则散落在业务代码中。闭集枚举映射避免 Prompt 注入，Prompt 文件便于版本化与 eval。

### 4. Preserve deterministic behavior when programming is disabled

关闭时注入明确的“无固定编程语言偏好”策略，代码题可沿用题面指定语言；题面没有指定时保持当前默认行为。这比完全省略配置更容易在不同入口保持一致，也不会改变非代码题。

### 5. Validate with contract, prompt, and UI tests

后端测试覆盖默认值、非法组合、状态锁、所有权、持久化和重启继承；Prompt 测试覆盖六种语言、非代码题不强制代码、Chat/Screenshot/英文面试组合；Web 测试覆盖开关、条件选择器、保存、刷新恢复和失败提示。AI eval 只使用合成算法题，不保存真实面试内容。

## Risks / Trade-offs

- [模型仍可能忽略所选语言或混入另一语言语法] → 使用明确闭集策略、代码围栏要求和合成 eval 门禁；首期不引入昂贵的编译执行服务。
- [截图视觉模型在二阶段 Prompt 前直接产出代码] → 同一编程策略同时进入视觉直答入口，避免只约束 Chat Builder。
- [滚动部署时旧后端或旧 Web 不认识字段] → 数据库先增加兼容默认列；请求字段可选；响应缺失时 Web 回退关闭状态。
- [把所有技术问题误判为代码题] → Prompt 明确只对要求实现、算法或代码修改的题目生效，非代码题继续自然回答。

## Migration Plan

1. 增加向前迁移列和约束，历史会话默认关闭编程。
2. 部署兼容旧请求的后端、Prompt 资产和测试。
3. 部署准备页控件，执行六种语言的合成 Chat 与 Screenshot smoke test。
4. 回滚时先隐藏 Web 控件；后端字段与数据库列保留，旧客户端继续按关闭状态工作。

## Open Questions

- 首期不提供 Kotlin、C#、Rust 和 Swift；可根据用户数据在后续闭集迁移中增加，不影响当前 API 形态。
