## Why

当前网页、桌面助手和实时发布通道可能分别保留不同的历史 session，导致页面显示已绑定但助手仍向旧面试推流。进入每场面试时需要由用户在网页明确选择设备，并由后端保证同一用户同一时间只有一个有效实时面试连接。

## What Changes

- 准备页提供“一键连接上次设备”和“输入新的机器码”两个用户可选入口。
- 两个入口统一创建本场的新设备绑定，不复用上一场 publisher token。
- 后端在新绑定时使该用户和该设备的其他绑定及 publisher 失效，保证单用户单 active realtime interview。
- 桌面助手检测 binding session 变化后停止旧 publisher；旧 token 永久失效时停止重连并等待当前 binding 建立新 publisher。
- 网页只允许当前 session 的实时订阅继续运行，并在 session 被替换时立即退出旧工作台。

## Capabilities

### New Capabilities

- `single-interview-device-connection`: 定义用户显式选择上次设备或输入机器码、单用户单实时面试租约及客户端切换恢复行为。

### Modified Capabilities

- `streamlined-interview-entry`: 准备页增加明确的设备选择和连接成功前置条件。

## Impact

- Web：面试准备页、设备连接状态、Backend Adapter 和恢复提示。
- Backend：Realtime Speech 设备查询、绑定切换、旧 publisher 吊销和单用户 active binding 约束。
- Desktop：binding 切换检测、publisher 终止错误分类和重建策略。
- Protocol/API：增加当前用户最近设备查询，不在客户端保存服务端密钥。
- Privacy：不新增音频、转录或设备敏感数据保存；只复用当前账号已绑定设备的安全摘要。
