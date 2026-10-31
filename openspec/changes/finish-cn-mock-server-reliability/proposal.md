## Why

国服模拟面试复查确认三项不需更新助手即可处理的问题：提交回答后仍等待旧ASR关闭（最长30秒）、已断开收音socket清理可能二次报错，以及生成失败缺少安全分阶段诊断。用户2026-10-31授权先完成这些代码，合并已本地完成的网页权限/播放修复，供先行上线使用，助手另行优化。

## What Changes

- 国服有效提交先停止交互、隔离旧capture，再发布生成状态并开始下一题；旧ASR异步关闭且保持有界跟踪与可回收。
- 收音端点兼容已断开socket的幂等关闭，不影响替代连接。
- 为简历读取、模型排队、请求、解析、校验和清理增加固定字段诊断，区分超时/HTTP/格式错误，不记录用户内容、凭据或原始异常。
- 保留已完成的[网页修复](../fix-mock-web-permission-readiness/proposal.md)，完成组合验证与本地上线交接。

## Capabilities

### New Capabilities

- `cn-mock-server-reliability`: CN模拟面试轮次推进、清理和隐私安全诊断的最小补修。
- `cn-mock-production-release`: 用户2026-11-01授权追加的国服固定镜像增量发布、用户保护及可回退验收。

### Modified Capabilities

无。沿用已有mock-turn-latency-recovery设计边界和国服固定计费/截止时间行为，不修改题目、评分或供应商策略。

## Impact

仅CN模拟面试专用runtime/routes/generation/jobs/diagnostics及测试、规范和交接记录。无助手、普通面试/笔试/资料/简历优化、国际服、Prompt/模型、收费/配额、数据库迁移、配置或依赖改动。不调真实模型、音频或用户数据。本轮完成开发自测与可审查交接，不自动操作线上或Git。生产发布仍须以目标实际镜像与静态资源图为基线，沿用[当前组件来源](../../../docs/current-cn-baseline.md)。证据和未解决边界见[上轮复查](../../../docs/releases/cn-mock-permission-local-20261030.1.md)。

## 2026-11-01 授权追加

用户已明确要求「你更新部署到国服吧」。将本变更与已完成网页修复合并，仅发布国服Backend/Web模拟面试增量；先完成固定候选和验收，通过全部用户工作门禁后切换。新增生产能力 `cn-mock-production-release`，不发布助手/国际服、不提交推送Git，原有非目标保持。
