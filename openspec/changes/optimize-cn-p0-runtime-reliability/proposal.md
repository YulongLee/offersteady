## Why

国服面试中的资源监控目前把主机内存当作容器内存展示，无法判断单个会话是否泄漏；面试结束后的连接回收也需要可验证的终态。同时，快答从用户点击到首屏显示仍有可感知延迟。现在处理这些 P0 问题，可以在不改变现有页面和面试流程的前提下提升稳定性与可观测性。

## What Changes

- 将容量面板的内存指标拆分为真实后端容器用量和主机可用内存，并在无 cgroup 限额时使用明确的容器 RSS 口径。
- 强化面试结束、取消和空闲回收的资源终态，关闭 ASR、SSE、桌面传输及会话专属后台任务，并记录回收结果。
- 梳理快答从点击、服务端接收、模型首 token 到浏览器首屏渲染的耗时，减少可避免的等待并保留分阶段诊断数据。
- 增加上述场景的回归测试和部署后只读验收指标。

## Capabilities

### New Capabilities

- `container-resource-observability`: 提供真实容器资源和主机资源的分离监控口径。
- `interview-resource-finalization`: 面试结束后可靠终止会话资源并可验证回收状态。
- `quick-answer-latency`: 记录并优化快答端到端首屏延迟。

### Modified Capabilities

<!-- No existing main capability spec covers these operational requirements. -->

## Impact

- 影响 `apps/backend/app/services/admin_capacity.py`、实时语音/快答服务及其生命周期管理。
- 影响管理平台容量接口返回字段和指标说明；保持现有核心业务 API 兼容。
- 不新增外部依赖，不改变前端视觉布局，不持久化原始音频、转录或个人信息。
