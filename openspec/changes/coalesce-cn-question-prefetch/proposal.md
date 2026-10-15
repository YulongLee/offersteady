## Why

2026-10-15 国服高峰只读诊断发现，17:00–17:10 有 5 次文字和 21 次截图回答启动，但执行 521 次知识检索；稳定字幕连续变化触发的过密预取，与后台请求/频繁建连共同增加共享资源工作量。用户已批准第一轮优化普通面试的预取调度与缓存正确性，完成本地测试后由用户晚上另行安排上线。

## What Changes

- 首个稳定问题及时提前检索，同一问题的连续更新合并为最新待办；限制同键运行/等待数量和全局状态，避免积压中间版本。
- 保留最终转写的及时预取、字幕/问题事件发布及点击快答的原有非等待路径；旧任务在安全边界失效，不能覆盖新问题。
- 缓存复用核对所有者、会话、问题和当前资料指纹，覆盖资料选择、版本、可用状态及集合变化；过期结果不能重新进入缓存。
- 补充合成并发、缓存、资料引用、快答及实际国服源码候选的本地回归与对照证据；明确局部检索收益不等于线上整体 P95 降幅。

## Capabilities

### New Capabilities

- `bounded-question-prefetch`: 首段先行、最新待办、有限等待、final 提示和有界安全调度。
- `material-safe-prefetch-cache`: 按身份、问题和资料版本正确复用预取，保留快答与详细回答行为。

### Modified Capabilities

无已归档对应主 Spec。保留 [快速回答启动](../reduce-live-quick-answer-first-visible-latency/specs/low-latency-live-answer-startup/spec.md) 和 [字幕/回答实时路径](../reduce-live-audio-to-answer-latency/specs/low-latency-live-audio-answer-path/spec.md) 的既有合同。

## Impact

Backend 普通面试 RealtimeSpeechService 的预取提交、新的小型有界调度器、ChatService 预取缓存及回归/评测。无新依赖、持久化资料、Prompt/模型/计费/音频采集策略变更；不改 Web/助手、轮询、数据库连接池或模拟面试出题。本地使用合成材料与隔离数据库验证，不调用真实模型/音频服务。用户于 2026-10-15 在本地验收完成后明确授权线上部署，增加仅国服 Backend 的实际镜像校验、活动门禁、最小更新、回退及发布后验证；不发布 Global 或其它组件。实际国服 `eb242…` 源码基线用于独立候选核对，禁止整文件覆盖无关能力。
