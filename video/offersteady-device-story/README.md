# 面试稳 · 设备使用演示

49 秒中文横版，1920×1080 / 30fps。用户要求自主设计，未使用 video-shotcraft 制作工作流。

- [中文配音版](out/offersteady-device-story-voice.mp4)
- [独立旁白](out/offersteady-device-story-narration.wav)
- [配音脚本](voiceover-script.md)
- [音乐版](out/offersteady-device-story.mp4)
- [静音版](out/offersteady-device-story-silent.mp4)
- [封面](out/poster.jpg)
- [播放预览](out/index.html)
- [分镜设计](design.md)

主线是电脑助手与手机网页配合使用，平板和电脑网页作为另外两种查看选择分别展示。画面使用当前 React 页面和电脑助手源码，在独立 Vite 采集配置中注入合成演示数据；未访问生产 API、录音或真实账号。影片是经剪辑的使用流程示意，不是实时端到端录屏。没有改动业务代码或部署网站。

连接码 628391 为合成示例。桌面输入状态由 monitor-fixture.ts 提供，页面中的回答取自合成项目资料。安装步骤通过字幕说明和安装后助手界面呈现，没有复刻操作系统安装向导。不同查看设备不会同时声称拥有活跃实时页。

音乐沿用前一视频工程的音频，来源记录见 [音频说明](public/audio/ATTRIBUTION.md)。原版无旁白；新增中文配音版，所有步骤仍可静音理解。

复现：在此目录运行 `npm run typecheck` 和 `npm run render`。本机 node_modules 链接复用前一视频工程；独立迁移时使用 npm install。素材已经固定在 public/textures。采集配置只用于本地素材制作。
