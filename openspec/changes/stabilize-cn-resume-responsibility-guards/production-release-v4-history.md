> 历史已失败候选，禁止用作当前上线规范。当前以[正式规范](production-release.md)及R12为准。

# 国服简历优化稳定性发布规范

用户本轮明确授权：继续优化，自测通过后上线。当前为准备/QA阶段，不代表已通过真实质量或已切换。

仅CN Backend，固定原容器2a907032… / image6f9a55d8…，Web88ae70/2124eee8…及其它6组件均非目标。新鲜baseline、完整231源/202schema/340Settings/315静态/NGINX/全部签名在artifacts/cn-resume-responsibility-20261019/current-baseline.json，SHA为 `013f0b4586266ab681cc6f9d6d48c98647cc1d5bff8f65ef9056de21b7ab4cf3`。只允许下列7源，231→236，原229输入保持；无配置/依赖/DDL/费用/Web/Global/助手/模拟面试/Git变更。

| 源 | SHA-256 |
| --- | --- |
| ai/prompts/resume-optimizer/review.zh-CN.v3.md | c18ed5e8544f85de1981382f14532dee73e41ddad7d4b1f01ba8b95d8031de06 |
| ai/prompts/resume-optimizer/review.zh-CN.v4.md | 3c71da05bc4c46227e27a96fea4b557b8965f6b768edb6cb3b21f21b948f9bbf |
| apps/backend/app/schemas/cn_resume_optimizer_provider_v3.py | 2ce9dbaaf32488e5a333c6f85b03bd0bf123fa77006ee4ae83ee2c979c761e75 |
| apps/backend/app/services/cn_resume_optimizer_anchors.py | 93f5dee46a5e9fe85f0f5f7ac565af6e62521e24bc3d293bd4f681d0e7f80c50 |
| apps/backend/app/services/cn_resume_optimizer_provider.py | a301c476273cfd98d04e041dfbe9d9d6f3742f8b1d2060f1994aed224b165d52 |
| apps/backend/app/services/cn_resume_optimizer_responsibility.py | ccc9629dde987d2e7ba3e2b1f5f234a9ba080e220515a20055707f5feccf970f |
| apps/backend/app/services/cn_resume_optimizer_service.py | 82d43d5262428ae71da9fef223ceef3dd8a37b560799d4839c03d300787bfbfc |

候选 `sha256:b78ccd9e35c187c7da7d83bd480a193b705976cdbeefc2e5373f9c2dfafbbe23` 已由实际6f9固定父digest构建并通过实际禁网/只读/无lifespan七副作用0、完整源/schema/Settings/10PDF同字节14页/原Word/双get及Linux单root挂载检查；真实8例QA尚待实际结果，全部通过才可冻结发布acceptance。不得换成未验收或旧v3质量失败镜像。

正式发布器复用[既有保护规范](../add-cn-resume-delivery-template/production-release.md)第3–5节的完整归属/全部Config/HostConfig/Mounts/网络、image-only overlay、排他锁、原完整七门禁、临近真实TCP8000/netns检查、严格已退出进程证明及受保护固定旧digest恢复。switch/recovery/ownership/tcp/gate函数保持原0fee控制器AST；只改本轮输入验收、候选引用、probe236和service最小fresh版本传参验证。prepare仅为已验收QA immutable image创建本轮专属tag并核实际image，不重新build另一候选，不改变生产。

本轮独立根 /opt/offersteady/releases/20261019-cn-resume-stability-1，payload/input/支持文件/控制器/plan双向哈希绑定，精确拒绝缺失/额外/符号链接；私有文件0600/根0700，env及Compose原文和日志不离服务器。新tag和回退tag专属于本轮，冻结旧6f9；不移动共享tag。服务整模块相对实际基线只新增fresh payload promptVersion传参，默认PDF分发和金融/取消/导出等保持。

preflight与临近切换分别重新核完整基线+完整七门禁+实际TCP/netns读数；busy只等待，不结束用户/清活动/改TTL。unknown/readfail/drift立即停止。不得复用旧门禁快照。只对精确归属且已知可恢复健康/公共验收失败，在所有保护重新通过时恢复6f9；未知或恢复失败停止并报告，不删数据/重放/改变费用。

实际切换后验证同一新容器/b78候选、healthy/restart0、236源/202schema/340配置与315静态/NGINX/7非目标/共享tag；原七公共入口200及匿名能力/导出401/private,no-store。必要代理DNS刷新仅沿用原nginx-t/reload条件，不改配置。短时仅脱敏ERROR/traceback/5xx及固定诊断计数，记录秒数和截断范围。真正通过后更新任务/验收/发布记录通知用户，不把短观察或8例合成样本当所有真实用户成功率。
