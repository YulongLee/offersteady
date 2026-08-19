# 工程岗位面试专题编辑说明

更新时间：2026-08-19

## 主题边界

| 页面 | 主要意图 | 核心内容 | 主要来源 |
| --- | --- | --- | --- |
| `/interview-questions/java-backend` | Java后端面试准备 | 语言、并发、JVM、数据与系统可靠性 | Oracle Java教程、JLS、JDK文档 |
| `/interview-questions/frontend` | 前端面试准备 | Web平台、事件循环、渲染、状态、性能与可访问性 | MDN Web文档 |
| `/interview-questions/algorithms` | 算法题解题与表达 | 澄清、数据结构、正确性、复杂度、编码与测试 | MIT OpenCourseWare |

内容不提供特定公司的泄露题库，不编造候选人项目、流量、性能或录用结果。涉及语言、JVM、浏览器、框架和API时需说明版本边界；涉及项目时要求读者使用可核对的个人经历。

## 发布结构

每篇包含直接准备框架、主题地图、典型追问、工程或正确性诊断、项目表达、FAQ、来源说明与至少五个内部链接。页面继续使用零运行时JavaScript的静态模板，单篇HTML不超过20 KB。

## 发布性能基线

`/interview-questions/frontend` 的生产构建 Lighthouse 结果：移动端与桌面端 Performance、Accessibility、Best Practices、SEO 均为 100；移动端 LCP 903 ms，桌面端 LCP 243 ms，TBT 0 ms，CLS 0。
