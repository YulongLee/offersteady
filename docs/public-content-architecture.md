# 公开内容与 SEO/GEO 信息架构

更新时间：2026-08-19

## 目标

公开内容同时服务两条路径：产品页面帮助访客理解、评估并开始使用；内容页面回答面试准备与技术专题问题，再引导到适合的产品能力。公开内容不得依赖登录态，不复制动态价格或桌面版本，也不得影响登录后的面试、资料、支付和会员功能。

## 当前入口

| 入口 | 主要意图 | 内容边界 |
| --- | --- | --- |
| `/` | 理解产品定位并开始体验 | 首页只陈述稳定产品事实 |
| `/features` | 了解产品能做什么 | 汇总准备、实时语音、截图回答与复盘能力 |
| `/interview-questions` | 理解面试题和技术专题框架 | 只推广已经发布的子内容，不提供空页面 |
| `/guides` | 查找面试方法、设备与平台排查指南 | 与产品操作手册分离 |
| `/guide` | 查询具体产品操作 | 登录、资料、助手、面试、截图、计费与隐私操作 |
| `/pricing` | 评估积分和会员 | 当前价格与权益以登录后页面为准 |
| `/download` | 了解电脑助手下载 | 当前版本和架构以产品下载中心为准 |
| `/security` | 理解数据与权限边界 | 不暴露私有 API、用户信息或内部实现 |

## 内容树

```text
面试稳AI助手
├── 产品功能 /features
│   ├── AI面试助手
│   ├── 实时面试辅助
│   ├── 截图回答
│   └── 面试复盘
├── 面试题与专题 /interview-questions
│   ├── 大模型面试题 /interview-questions/llm
│   ├── RAG面试题 /interview-questions/rag
│   ├── AI Agent面试题 /interview-questions/ai-agent
│   └── 其他子专题只有在内容完整、审核与发布检查通过后才开放
├── 面试指南 /guides
│   ├── 面试准备、自我介绍与常见问题
│   ├── 项目经历、技术面试与 STAR 回答结构
│   ├── 收音与系统权限
│   └── 远程面试平台设置
└── 产品使用手册 /guide
```

## 发布要求

每个可索引公开页面必须包含唯一标题和描述、一个 H1、自规范链接、可解析的 JSON-LD、可抓取内部链接、边界说明、Sitemap 条目和明确的 Nginx 路由。目录与短专题 HTML 预算为 12 KB，深度指南为 20 KB，共享样式预算为 8 KB。

发布前运行：

```bash
npm run test:seo-p0 -w @offersteady/web
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=0.1.0 npm run build -w @offersteady/web
openspec validate <change> --strict
```

上线后逐项确认公开路由返回 200、自规范链接正确、登录页维持 `noindex`、未知路径返回 404。内容子页未达到可独立解决问题的标准时，不创建占位路由。

## 2026-08-19 内容入口性能基线

生产构建后的 `/features` 静态文档通过 Lighthouse 检查：

| 模式 | Performance | Accessibility | Best Practices | SEO | LCP | TBT | CLS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mobile | 100 | 100 | 100 | 100 | 903 ms | 0 ms | 0 |
| Desktop | 100 | 100 | 100 | 100 | 243 ms | 0 ms | 0 |

测量环境为本机 Vite production preview 与 headless Chrome；它用于防止构建回退，不替代线上真实用户监控。
