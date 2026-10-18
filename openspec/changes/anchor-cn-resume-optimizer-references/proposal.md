## Why

国服简历优化当前要求模型逐字返回评分/建议引文及唯一改写引文；模型复制原文时容易改变空白、漏字或选择重复句，结果会被安全守卫拒绝。本轮将“定位原文”交给服务端，模型只选择服务端提供的片段编号，减少引用错误，同时保留全部事实、失败退款与安全局部改写规则；不据此推断任何旧用户失败的精确原因。

## What Changes

- 对任务已冻结的规范化简历/JD建立确定性、完整保留原文的连续片段与服务端可信位置表；内部Provider v3的评分、建议依据和改写只引用编号，服务端重建原public引文，并只按可信位置替换。
- 为v3新增独立严格内部schema、中文Prompt及合成eval，保留v1/v2原路径。升级的是唯一原文定位方式，不是事实匹配：不模糊搜索、不接收模型offset、不归一化或截断原文，不放宽数字/技术/机构/责任/联系方式及最终稿守卫。
- 保留原public结果/API、评分、会员每日3次/其余100积分、owner/source/claim/revision/取消删除、partial成功及零有效失败原路退款、历史稿与当前商务PDF/DOCX；无新UI、DDL、依赖、配置或并发预算。
- 本轮只本地开发/隔离自测。可选质量阶段最多6个独立纯合成用例各1次，必须另有root的候选/Prompt/script/case冻结和QA GO、禁网候选先验及调用前完整七门禁空闲；任何失败或不确定停止，不以重复采样碰运气。本change不授权生产切换或Git。

## Capabilities

### New Capabilities

- `cn-server-anchored-resume-review`: 国服服务端原文片段、v3引用验证/可信位置改写、旧版兼容、预算与有界合成质量验证。

### Modified Capabilities

无已归档主能力直接改写。本能力在[原CN合同](../add-cn-resume-optimizer/contract.md)、[失败诊断](../add-cn-resume-optimizer/failure-diagnostics.md)与[安全局部改写合同](../add-cn-resume-optimizer/safe-edit-application.md)之上增加v3定位路径；仅v3以可信ID唯一span替代模型quote逐字计数，旧版本合同不静默回写。

## Impact

预计仅影响CN Backend内部schema、Provider/原事实校验复用及Runtime最小版本传递、新CN Prompt/evals和纯合成/隔离PG/API测试。主仓负责规范；实现源以CN工作区与新鲜实际运行基线为准，不把混合主仓源码覆盖国服。

本轮只读基线 `artifacts/cn-resume-optimizer-anchors-20261019/current-baseline.json` SHA `ae973bcfb50949682459afe2ca744bcc673b8727e201af9488d3de0b8a75df70` 已绑定实际Backend2a907/6f9a、231完整输入、202完整schema、340Settings、315Web静态及7非目标，原商务模板保持。执行前须root读完整apply context、双根strict并明确本地实施GO；候选、测试、真实合成QA与上线均不得预称已完成。
