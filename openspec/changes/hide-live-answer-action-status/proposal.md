## Why

实时面试页会在快答和截屏回答入口旁持续展示“已回答”“快答已完成”“截屏回答已完成”等过程或结果状态，抢占面试时的注意力和垂直空间。用户已经能从回答区域看到结果，因此这些状态属于重复信息，应从现场界面移除。

## What Changes

- 实时面试进行中，快答入口不再显示处理、成功、取消或失败状态文案，也不把按钮标题改成“快答中”或“已回答”。
- 截屏回答入口不再展示处理、完成或取消状态文案。
- 保留按钮禁用、防重复提交、回答展示、截图失败恢复和内部任务状态，不改变快答或截图回答业务链路。
- 同时覆盖桌面和移动端实时面试工作区。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `resizable-live-interview-workspace`: 实时工作区的快答与截屏回答入口保持安静、稳定，不向用户展示重复的任务状态。

## Impact

- Affected code: `apps/web/src/AnswerActionBar.tsx`、移动端复用该操作栏的相关组件及 Web 回归测试。
- APIs/dependencies: 无变化。
- Privacy: 不新增音频、截图或个人信息的采集、传输或保存。
