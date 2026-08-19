# AI 技术面试专题编辑说明

更新时间：2026-08-19

## 主题边界

| 页面 | 主要搜索意图 | 核心边界 | 主要来源 |
| --- | --- | --- | --- |
| `/interview-questions/llm` | 大模型原理与工程面试 | 模型机制、推理、上下文、幻觉、评测 | Transformer、Lost in the Middle、NIST GAI Profile |
| `/interview-questions/rag` | RAG架构与故障定位 | 摄取、切分、召回、重排、生成、引用、评测 | RAG、RAGAS、Lost in the Middle |
| `/interview-questions/ai-agent` | Agent架构、安全与恢复 | 工作流、工具、状态、恢复、权限、可观测性 | ReAct、LangGraph官方文档、NIST GAI Profile |

三篇文章不提供特定公司的泄露题目，不把框架文档当作通用标准，不虚构项目经验或性能数据。内容以稳定概念和诊断方法为主；版本化工具与模型信息仅在确有必要并完成复核时加入。

## 内容结构

每篇文章提供直接定义、面试回答框架、组件或链路、工程取舍、故障诊断、评测、FAQ、来源说明和相关页面。技术结论必须能追溯到原始论文、标准或官方文档，并明确研究条件与真实工程场景之间的差异。

## 内部链接

三个主题互相链接，并连接到技术面试准备、项目经历表达、面试资料准备、AI面试助手能力与登录练习入口。未来的Java后端、前端和算法专题只有在内容与发布检查完成后才从主题目录开放。

## 发布性能基线

`/interview-questions/rag` 的生产构建 Lighthouse 结果：移动端与桌面端 Performance、Accessibility、Best Practices、SEO 均为 100；移动端 LCP 903 ms，桌面端 LCP 242 ms，TBT 0 ms，CLS 0。测试基于本机 production preview，用于发布防回退。
