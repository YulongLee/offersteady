# 关键词与页面映射

下表是意图映射，不包含未经数据源验证的搜索量、难度或排名预测。

| 主要意图 | 辅助表达 | 目标页面 | 页面角色 |
| --- | --- | --- | --- |
| AI 面试助手 | 面试辅助工具、智能面试助手 | `/features/ai-interview-assistant` | 核心能力总览 |
| 实时面试辅助 | 实时语音识别、面试问题整理 | `/features/realtime-interview` | 实时工作流与边界 |
| 截图回答 | 截图解题、在线笔试截图题 | `/features/screenshot-answer` | 截图链路说明 |
| 面试复盘 | 面试记录、问答复盘、复盘下载 | `/features/interview-review` | 面试后价值页 |
| 面试收音问题 | 系统音频、麦克风权限、收音排查 | `/guides/audio-troubleshooting` | 高意图故障排查 |
| 面试准备 | 简历 JD、知识库、面试资料 | `/guides/interview-preparation` | 面试前准备指南 |
| 产品安装与完整操作 | Windows、macOS、积分会员、支付 | `/guide` | 权威使用手册 |
| 积分与会员 | AI 面试助手收费、积分消耗、会员权益 | `/pricing` | 稳定计费逻辑与动态价格入口 |
| 电脑助手下载 | macOS 面试助手、Windows 面试助手、安装权限 | `/download` | 下载决策与安装入口 |
| 数据安全与隐私 | 面试录音保存、截图隐私、资料安全 | `/security` | 数据处理与安全边界 |
| 产品身份 | 面试稳是什么、面试稳AI助手 | `/about` | 产品定位与公开身份 |
| 产品支持 | 面试稳客服、订单问题、安装问题 | `/contact` | 官方支持入口 |
| macOS 面试权限 | 麦克风权限、屏幕与系统音频录制 | `/guides/macos-permissions` | macOS 权限排查 |
| 飞书面试收音 | 飞书面试官声音、飞书音频设置 | `/guides/feishu-audio-setup` | 飞书用户侧设置指南 |
| 腾讯会议面试收音 | 腾讯会议面试官声音、会议音频设置 | `/guides/tencent-meeting-audio-setup` | 腾讯会议用户侧设置指南 |
| STAR 面试回答 | STAR 法则、结构化面试回答 | `/guides/star-interview-answer` | 面试表达方法指南 |

## 映射规则

- 每个 URL 只承担一个主意图，避免内部页面互相竞争。
- 页面标题和 H1 使用自然中文，不重复堆叠同义词。
- 所有页面链接到首页、使用手册和至少两个相关主题页。
- 不使用“隐身、不可检测、保证成功、秒级、完全准确”等无法验证或不符合产品边界的表达。
