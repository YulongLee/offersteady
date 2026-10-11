# 国服资源中心首批技术报告

状态：首批内容草稿，待产品确认后再接入 `/guides` 或新的 `/resources` 栏目。

## 目标

把首页“查看更多资源”扩展为公开的技术报告入口，覆盖求职者在使用 AI 面试工具和准备技术面试时会主动搜索的问题。内容先解决问题，再自然引导到对应功能，不把文章写成硬广。

目标读者：中文求职者、技术面试候选人、需要排查音频与资料处理问题的用户。

业务目标：

- 获取“问题 + 排查方法”类长尾搜索流量；
- 让读者从报告进入实时面试辅助、资料库、下载和面试指南；
- 用公开、可核对的技术解释建立信任，再引导注册或开始准备。

## 首批文章

| 优先级 | 文件 | 主要搜索意图 | 建议承接页 |
| --- | --- | --- | --- |
| P0 | `api-p95-latency-diagnosis.md` | API P95 高、接口长尾、接口响应慢排查 | `/features/realtime-interview`、`/guides/technical-interview` |
| P0 | `container-memory-not-falling.md` | 容器内存不回落、Python 内存泄漏排查 | `/security`、`/guides` |
| P1 | `resume-pdf-parsing-failures.md` | PDF 简历解析失败、一直解析中 | `/app/library`（登录后）、`/guides/interview-preparation` |
| P1 | `mac-microphone-permission.md` | Mac 麦克风权限、没有授权弹窗 | `/guides/audio-troubleshooting`、`/download` |
| P1 | `realtime-interview-polling.md` | active-connection、前端轮询、请求量大 | `/features/realtime-interview`、`/features/ai-interview-assistant` |

## 发布顺序

先发布两个能直接回答线上常见疑问的 P0 页面，再发布资料处理和设备排查内容。每篇上线前需要：

1. 配置唯一标题、描述、H1、canonical 和 `Article`/`BreadcrumbList` JSON-LD；
2. 加入 2–4 个相关站内链接，并从 `/guides` 或专题目录反向链接；
3. 检查文章中的数字、性能结论和产品权益，不把合成测试写成线上 SLA；
4. 加入 sitemap，使用普通用户和搜索爬虫各检查一次 200、正文可见和没有 `noindex`；
5. 发布后记录索引、展现、点击和注册，不把“已提交”当成“已排名”。

## 内容边界

- 不放用户简历、面试录音、内部 token、真实日志或可识别个人信息；
- 不承诺“保证通过面试”“保证排名”或未经验证的性能提升；
- 公开页面只描述稳定产品事实，动态价格和个人权益仍以产品页面为准；
- 文章中的示例数据均为合成示例，不能解释为线上用户数据。

## 后续内链结构

```text
首页“查看更多资源”
└── 技术报告 /resources
    ├── API P95 与长尾排查
    ├── 容器内存不回落
    ├── PDF 简历解析失败
    ├── Mac 麦克风权限
    └── 实时面试轮询优化
```

暂不改动首页代码；本目录先作为内容审核和发布输入。页面结构、路由和 sitemap 在文章确认后单独走 OpenSpec 变更。
