## Why

将本地伴随程序封装为 1.3.0，验证已经在工作区实现的控制面低频、单飞轮询策略，便于用户在本机测试而不触碰线上服务。

## What Changes

- 将桌面伴随程序版本更新为 `1.3.0`，仅影响本地构建元数据。
- 保持绑定等待与 live 状态的控制面轮询为 10 秒单飞调度，并保留失败退避及用户操作后的即时刷新。
- 增加/更新轮询策略回归验证，确认音频采集、ASR、截图和网页协议不被改变。
- 生成本地开发包并在本机打开供验收；不上传 OSS、不更新发布清单、不重启线上服务。

## Capabilities

### New Capabilities

- `companion-1-3-0-local-release`: 定义本地 1.3.0 版本元数据、控制面轮询策略与本地构建验收行为。

### Modified Capabilities

<!-- No established main spec requirements are changed. -->

## Impact

- Desktop: `apps/desktop` 版本元数据、本地构建与绑定轮询策略测试。
- Tests/docs: 增加 1.3.0 本地验证记录；不涉及后端、线上服务或用户数据。
