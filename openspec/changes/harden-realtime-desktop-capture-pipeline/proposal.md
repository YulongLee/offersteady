## Why

当前面试页可以完成机器码绑定，但实时对话仍长期停留在“等待麦克风或电脑输出出现可识别声音”，截图回答也会失败。最新分段诊断显示：后端 Realtime Speech、publisher 创建、session 绑定和合成 PCM 探针可用，真实桌面采集却没有稳定产出 `frameReceipts`，因此产品核心链路没有真实闭环。

这已经超过调 UI 文案或降低阈值能解决的范围，需要把实时采集、ASR、网页消费和截图回答作为一条可测试链路整体加固。

## What Changes

- 将桌面伴随程序的实时音频主链路从 Electron `getUserMedia/getDisplayMedia` 采集升级为可验证的 macOS 原生采集 runtime 主链路，Electron 保留为 UI、绑定和兜底探测层。
- 为麦克风、电脑输出、后端 frame ingest、ASR、网页实时展示分别建立独立健康检查和失败原因，不能再以“已绑定”代表“可实时对话”。
- 增加端到端诊断：同一 session 下必须能验证真实麦克风帧、真实系统输出帧、后端 `frameReceipts`、ASR accepted/transcript、网页实时对话渲染。
- 加固截图回答链路：网页创建远程截图请求、桌面轮询、原生/桌面截图、上传后端、视觉模型回答、网页显示，任一失败必须返回明确阶段原因。
- 保留用户原型和现有面试流程，不改变入口、机器码绑定方式、实时对话区域和截图按钮的基本交互。
- 不在客户端存放 ASR、视觉模型或后端密钥；不持久化原始音频和未确认截图诊断材料。

## Capabilities

### New Capabilities

- `realtime-desktop-capture-pipeline`: 桌面伴随程序到后端 ASR、网页实时对话的端到端采集、发布、诊断和降级能力。
- `remote-screenshot-answer-pipeline`: 网页面试页发起远程截图回答，由桌面助手截图、上传并由后端视觉模型生成回答的端到端能力。

### Modified Capabilities

- None.

## Impact

- Desktop: `apps/desktop` 的 macOS native runtime、Electron renderer、音频采集适配器、远程截图轮询和打包脚本。
- Backend: `apps/backend` 的 realtime speech、screenshot answer、runtime diagnostics、ASR/vision provider probe 和 session-scoped 状态接口。
- Web: `apps/web` 的 live 页面实时对话消费、截图回答请求、失败弹窗和诊断提示。
- Protocol: 可能需要补充 source health、frame receipt、capture request stage、diagnostic result 的字段，但保持向后兼容。
- Docs/tests: 增加本地端到端测试脚本和隐私安全说明；测试只保存计数、耗时、错误码，不保存原始音频或截图内容。
