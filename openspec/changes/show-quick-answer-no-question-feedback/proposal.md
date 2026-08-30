## Why

实时面试中没有手动问题、也尚未识别到面试官问题时，快答按钮当前被直接禁用，用户点击不了，也得不到原因反馈，容易误以为功能没有完成或已经失效。

## What Changes

- 空问题状态下保持快答入口可触发；用户点击后不发起回答、不扣费。
- 明确提示“未能识别到面试官的问题”，并引导用户等待语音识别或手动输入问题。
- 用户输入问题、识别到面试官问题或成功启动其他操作后，清除该提示。
- 保留回答处理中防重复提交以及之前对常规处理/成功状态的隐藏规则。
- 同时覆盖桌面端和移动端实时面试界面。

## Capabilities

### New Capabilities

- `quick-answer-empty-feedback`: 定义快答在缺少可回答问题时的可见、可恢复且不产生计费的反馈行为。

### Modified Capabilities

无。

## Impact

- `apps/web/src/AnswerActionBar.tsx`、`apps/web/src/MobileInterviewControls.tsx`：允许空问题时触发快答意图。
- `apps/web/src/App.tsx`：展示并清理缺少面试官问题的提示。
- Web 组件与实时工作区回归测试。
- 不修改 ASR、回答 API、计费规则、音频采集或数据保存方式。
