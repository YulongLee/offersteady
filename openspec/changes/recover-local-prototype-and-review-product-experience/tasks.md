## 1. Prototype recovery baseline

- [x] 1.1 定位本地 Web 原型当前的启动、编译、路由或页面崩溃问题，并确认受影响的核心路径
- [x] 1.2 恢复首页、登录、资料库、面试准备、实时面试、积分/充值、下载入口和使用说明的已批准页面结构与交互顺序
- [x] 1.3 收敛原型页面与适配层边界，避免为兼容工程接入而继续改动已批准原型体验

## 2. Product function review

- [x] 2.1 按完整用户旅程巡检主要页面与流程，记录每条路径是否可用、是否偏离产品意图
- [x] 2.2 将 review 发现分类为“必须立即恢复的问题”和“需要后续单独决策的问题”
- [x] 2.3 补充受保护原型基线说明，明确后续不得在未开新变更时静默修改的页面行为

## 3. Verification and handoff

- [x] 3.1 运行本地原型验证，确认关键页面能够稳定访问且主要流程可走通
- [x] 3.2 运行 `openspec validate recover-local-prototype-and-review-product-experience --strict`
- [x] 3.3 输出恢复结果、剩余差异点和建议的下一步处理顺序
