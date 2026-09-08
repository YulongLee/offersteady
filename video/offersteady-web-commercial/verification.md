# 最终交付验证

2026-09-07，针对最终交付文件。视频部分为36.000秒。

| 文件 | 大小 | 画面 | 帧数 |
|---|---|---|---|
| `offersteady-commercial.mp4` | 8.48 MB | 1920×1080 / 60 fps | 2160 |
| `offersteady-commercial-nobgm.mp4` | 7.91 MB | 1920×1080 / 60 fps | 2160 |
| `web/offersteady-web.mp4` | 3.25 MB | 1920×1080 / 30 fps | 1080 |
| `web/offersteady-web-720.mp4` | 1.36 MB | 1280×720 / 30 fps | 1080 |

- 四个 MP4 均完成全量 ffmpeg 解码，返回0且无错误；H.264 4:2:0（full range，ffprobe标记yuvj420p），moov均在mdat前，可渐进加载。
- 两个母版 AAC 48kHz；音乐版含背景音乐及音效，无旁白；无背景音乐版只含音效。AAC尾部填充约53ms，画面时间线相同。网页版无音轨。
- 最终音乐版实测 -21.23 LUFS，true peak -3.74 dBTP，单声道分析信号无满幅样本。母带+7dB已同步回源码；最后交付由ffmpeg复制原画面、增益并重编码AAC，无视觉重编码。
- 12个动作音效的源波形与最终仅音效MP4交叉相关，源RMS峰值加实际起点后，动作峰值误差绝对值最大0.46帧（60fps，约7.7ms）。反向riser使用1.7秒匹配窗口，其余0.3/0.9秒。
- 源采样峰值、输出偏移与最终相关回测分别保存；背景音乐未承诺每拍剪切。主观音色听感未通过可听工具检验，不将客观峰值检查冒充试听。
- 实际Chrome浏览器1280×900和390×844页面测试：播放时间持续推进，36秒/1920×1080元数据正确；seek到20.4秒后readyState=4，已解码199帧，无media error；页面无横向溢出。最终浏览器截图已目视复核，桌面正文可读；手机嵌入小窗宜全屏阅读详细示例。
- `npm run typecheck`通过。既有能力变更`refine-live-workspace-and-instant-screenshot`的OpenSpec严格校验通过。本任务仅增加独立视频工程，未更改产品行为或部署官网。
- 独立视觉终检见[final-review.md](final-review.md)。音视频检查原始数据见[out/qa/delivery-checks.json](out/qa/delivery-checks.json)、[loudness.log](out/qa/loudness.log)、[网页播放](out/qa/web/playback.json)。

## 边界

演示来自真实前端配合合成fixture，部分内容经过视频编辑性强调，不证明线上后端能力与延迟。所有字幕为烧录内容。原参考片仅用于分析，没有进入交付包。音乐与音效来源及许可快照均留档。
