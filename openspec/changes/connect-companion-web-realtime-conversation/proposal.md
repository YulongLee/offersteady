## Why

当前产品虽然已经有桌面伴随助手、机器码绑定和网页面试页，但三者还没有形成真实互通：用户进入面试后，桌面端采集到的“我”和“面试官”语音没有稳定进入网页实时对话区。这个缺口直接影响产品核心价值，因为用户看不到实时对话，就无法继续验证快答、实时回答和后续语音链路。

## What Changes

- 建立桌面伴随助手、后端 Realtime Speech 和网页实时对话区之间的端到端实时互通链路。
- 规定桌面端必须以双通道来源上报语音：麦克风/耳机输入映射为“我”，电脑输出音频映射为“面试官”。
- 规定网页端进入面试后，实时对话区必须优先展示当前 session 的真实实时转录，不再停留在占位或仅手动输入状态。
- 为实时对话链路增加连接状态、转录状态和失败诊断，便于区分“设备未采集”“后端未接收”“ASR 未返回”和“网页未消费”。
- 保持现有产品原型布局不变，只补齐真实数据流和运行契约。

## Capabilities

### New Capabilities

- `companion-web-realtime-sync`: 定义桌面伴随助手、后端 Realtime Speech 和网页实时对话区之间的双通道实时转录同步契约。

### Modified Capabilities

- `resizable-live-interview-workspace`: 实时对话区从原型占位显示升级为展示当前面试 session 的真实“面试官 / 我”双角色实时转录。

## Impact

- Affected desktop areas: `apps/desktop` 的设备绑定状态、实时发布链路、双通道 source 映射和运行诊断。
- Affected backend areas: `apps/backend` 的 realtime-speech runtime、session 绑定校验、转录事件流和当前 session 过滤。
- Affected web areas: `apps/web` 的实时对话轮询/订阅、live 页面状态聚合和当前 session 对话渲染。
- Affected protocol areas: `packages/protocol` 中桌面 source kind、runtime status 和 transcript role 的跨端契约。
- Privacy impact: 实时音频和转录仍按最小化原则处理，不默认保存原始音频；日志和诊断不得输出媒体内容本体。
