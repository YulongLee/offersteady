## Why

国服已完成并上线的问题预取合并、有限并发和资料安全缓存优化，可以减少连续转写产生的重复检索与共享资源负担。用户于 2026-10-16 明确要求将本轮优化同步到国际服并上线，需要以国际服实际运行镜像为基线验证后最小发布。

## What Changes

- 将已验证的 leading/latest/final 优先、有界预取与生命周期撤销同步到 Global 普通面试后台。
- 同步按 owner/session、完整问题和当前资料版本校验的预取缓存，保留用户点击快答非等待及 detail 独立检索。
- 保存国际服实际运行镜像和完整源码清单，只叠加获准三个 Backend 文件的相关节点；保护路由、所有非目标源码、Prompt、有效模型、运行配置和其它组件。
- 使用隔离合成回归、候选只读探针、即时活动门禁和可核验回退，测试通过后上线 Global Backend。

## Capabilities

### New Capabilities

- `global-question-prefetch-parity`: 国际服普通面试获得有界预取与资料安全缓存，同时保留 Global 独立产品行为。
- `global-prefetch-protected-release`: 以实际 Global 镜像为基线的最小 Backend 发布、无人使用门禁和回退验收。

### Modified Capabilities

无对应已归档主 Spec。复用 [国服有界预取](../coalesce-cn-question-prefetch/specs/bounded-question-prefetch/spec.md) 与 [资料安全缓存](../coalesce-cn-question-prefetch/specs/material-safe-prefetch-cache/spec.md) 的优化合同，保留 [国际服已有可靠性行为](../sync-global-mock-and-companion-1-3-5/specs/global-mock-turn-reliability/spec.md)。

## Impact

仅 Global Backend 的 `services/chat_service.py`、`services/realtime_speech_service.py`、新增 `services/question_prefetch_scheduler.py` 及其合成验证/发布支持与文档。无新依赖、API/协议、数据库迁移、用户数据清理或音频/转录持久化；不调用真实模型/语音供应商做测试。Global 收费/独立会员、语言、模型/Prompt、已关闭模拟面试开关保持；Web、三平台助手、Admin、worker、数据库/Redis、CN 全部不发布。共享研发源码只能提供优化节点，禁止整包或整文件覆盖国际服。
