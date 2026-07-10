## ADDED Requirements

### Requirement: Lead the closing landing section with user value
公开首页 SHALL 使用面向用户收益的价值模块替换以 `CLEAR BOUNDARIES` 和“不替你编造经历”为主标题的大面积卡片。该模块 MUST 直接说明产品如何帮助用户理解问题、组织回答和按求职节奏使用。

#### Scenario: Visitor reaches the value section
- **WHEN** 未登录访客浏览到首页核心介绍的收尾区域
- **THEN** 页面首先展示“实时抓住问题重点”“回答更贴合个人资料”“按求职节奏灵活使用”等直接收益，而不是以限制或数据保留规则作为主标题

#### Scenario: Visitor scans headings only
- **WHEN** 访客只阅读首页标题和卡片标题
- **THEN** 标题层级仍能表达实时理解、个性化回答和灵活使用三项核心价值

### Requirement: Keep product claims attractive and supportable
首页价值文案 SHALL 使用直观、积极且可验证的语言，并 MUST NOT 宣称保证获得 Offer、提供唯一标准答案、完全准确或替代用户真实经历。

#### Scenario: Marketing copy is rendered
- **WHEN** 首页加载当前发布的中文价值文案
- **THEN** 文案说明产品提供回答思路和现场辅助，且不包含结果保证或无法验证的绝对化表述

### Requirement: Preserve trust information as secondary content
首页 MUST 保留 AI 建议属性、真实经历边界、数据管理与删除入口，但 SHALL 将这些内容呈现为价值模块后的简短信任说明或可访问链接，而不是主要转化卡片。

#### Scenario: Visitor wants privacy details
- **WHEN** 访客从首页价值模块查看信任或隐私说明
- **THEN** 页面提供可访问的使用边界和隐私入口，并说明建议属性与数据控制，而不打断主要价值介绍

#### Scenario: Trust link is unavailable
- **WHEN** 隐私或使用说明目标页面暂时不可用
- **THEN** 首页仍展示最小必要的建议属性和真实经历说明，不得完全隐藏产品边界

### Requirement: Explain knowledge pricing at summary level
首页价格摘要 SHALL 说明知识材料索引 200 点起，并 SHALL 说明 15 天和 30 天会员各包含 2 份知识材料额度。完整 Token 公式 MUST 链接或引导至积分页，不得在首页用复杂公式干扰主流程。

#### Scenario: Visitor compares payment modes
- **WHEN** 访客浏览首页价格摘要
- **THEN** 页面同时说明按点知识材料起步价和长周期会员的两份知识材料权益，并提供查看完整规则的入口

