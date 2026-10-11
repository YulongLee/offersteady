## Why

国服模拟面试当前使用的 `qwen3-tts-instruct-flash-realtime` 已列入 2026-10-10 下线公告。用户已授权并要求替换为实测可调用的 `qwen-audio-3.0-tts-plus`，防止模拟面试提问朗读中断。

## What Changes

- 增加新模型的 inference 双工流式 TTS 适配；仅朗读已有题目，保持 24 kHz PCM 与当前浏览器协议。
- 国服显式配置新模型、inference 端点和女声音色 `longanhuan_v3.6`（龙安欢）；原 Cherry 音色不能沿用。
- 保留文本继续、错误脱敏、时长/并发/超时边界和取消清理，验证普通面试及旧协议不受影响。
- 基于实际运行中的国服后端镜像生成最小覆盖包；自测及真实提供商探针通过、无人面试后仅切换后端。
- 非目标：国际服部署、桌面助手升级、前端改版、出题/报告模型、积分规则、数据库变更、音频持久化、Git 推送。

## Capabilities

### New Capabilities

- `cn-mock-question-speech-migration`: 国服新 TTS 协议、失败回退与隔离发布要求。现有模拟面试规格仍在 `add-ai-mock-interview` 变更中，主规格尚无该能力；本规格明确替代其国服特定模型要求，不改动历史变更。

### Modified Capabilities

无主规格修改。

## Impact

仅后端 `MockInterviewTts`、国服三项 TTS 配置、合成评测/回归测试与发布记录。复用已有 WebSocket 库和服务端密钥，不添加 SDK。音频只在内存中流转；题目仍由原文本模型生成，用户回答仍由原 ASR 识别。服务商费用可能变化，产品积分定价不变。新声音的听感及真实设备验收由用户上线后确认，不承诺与 Cherry 完全一致。
