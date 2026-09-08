# 面试稳官网宣传片验证记录

验证日期：2026-09-03（Asia/Shanghai）

## 输出规格

- 带 BGM 版：`out/offersteady-promo.mp4`，1800 帧、30 fps、1920×1080、H.264 + 48 kHz 双声道 AAC，60.053333 秒，12,211,387 bytes。
- 无 BGM 版：`out/offersteady-promo-nobgm.mp4`，同规格，60.053333 秒，12,211,544 bytes；保留全部 SFX。
- 两版均通过 FFmpeg 全片解码检查，无错误输出。
- `npx tsc --noEmit` 通过。

## 双版本与声音

- 两版由同一 Remotion 时间轴渲染，仅 `bgm` 输入属性不同；画面源、镜头、字幕和 SFX cue 完全相同。
- 由于 H.264 独立编码存在细微量化差异，解码画面不是逐字节相同；双版本 SSIM 为 0.999817，PSNR 平均 60.34 dB，属于不可见编码差异。
- 带 BGM 音轨：mean -23.5 dB，peak -3.9 dB。
- 无 BGM / SFX-only 音轨：mean -30.6 dB，peak -6.4 dB。两版均无削波。
- 无旁白；静音叙事由全程大字幕与产品状态完成。

## MiniMax 配音版

- 文件：`out/offersteady-promo-voice.mp4`，1920×1080、30 fps、1800 帧、H.264 + 48 kHz 双声道 AAC，60.053333 秒，12,210,115 bytes。
- 旁白使用 MiniMax `speech-2.8-hd` 与系统音色 `male-qn-jingying`，分 9 段生成并按镜头钉帧；完整台词和时间见 `voiceover-script.md`。
- 旁白期间 BGM 平滑 duck 至原音量的 36%，SFX 保留；综合响度 -22.7 LUFS，LRA 6.0 LU，true peak -4.6 dBFS，无削波。
- 配音版通过 FFmpeg 全片解码；相对已通过的无旁白正式版，画面 SSIM 为 0.999957，差异属于独立 H.264 编码量化。
- 项目目录扫描未发现 API Key 或 Key 片段；密钥未写入源码、配置、音频元数据或验证文件。

## 音画补偿回测

- 渲染管线：Remotion 4.0.484 / H.264 / AAC / 48 kHz / MP4 / 30 fps。
- 时间轴统一使用 `OUTPUT_AUDIO_OFFSET_F = 1.28`；`sfxFrom()` 同时扣除输出音轨偏移与已知素材峰值滞后。
- 从最终 SFX-only 成片提取 48 kHz PCM，以 `click-camera.mp3` 的有效动作窗口做归一化互相关；未对 BGM beat 源时间做任何修改。
- 目标 341f → 音源起点 341.274f，误差 +0.274f。
- 目标 784f → 音源起点 784.284f，误差 +0.284f。
- 目标 1226f → 音源起点 1226.274f，误差 +0.274f。
- 三个跨片段探针均小于 0.3f 误差，没有累积漂移。
- 所有长音效均由 `Sequence.durationInFrames` 显式截断。

## 视觉与静音检查

- 源时间轴关键帧：52、136、236、356、456、566、684、824、936、1044、1152、1260、1342、1410、1538、1738。
- 最终 MP4 抽帧联系表：`out/qa/guided/render-contact-sheet-final.png`。
- 独立复审提出的复盘末卡裁切已修复；最终 MP4 的 1390、1410、1430、1440 帧复查表为 `out/qa/guided/review-fix-contact-sheet.png`，状态卡文字完整、无遮挡，转入收尾无异常。
- 已逐项检查品牌开场、实时声纹、三路资料汇聚、回答生成、截图扫描、灵活选择、复盘时间轴及三重稳收尾。
- 字幕独立表达完整叙事；辅助文字不承担唯一关键信息。开场与结尾均包含完整品牌主张。
- 金额场景只显示“成本价使用”“按次 / 按天 / 按节奏选择”，没有具体金额。
- 源码扫描未发现 `Math.random`、`Date.now`、`new Date` 或金额文案，渲染结果可复现。

## 数据安全

- 产品画面来自真实 React 页面与 CSS 的 capture-only 渲染，未修改业务页面。
- 价格区仅在截图 fixture 中脱敏替换。
- 面试题、回答、候选人、公司、简历、JD 与知识库内容均为合成示例。
- 未使用生产登录态、真实用户数据、音频、个人信息或密钥。
