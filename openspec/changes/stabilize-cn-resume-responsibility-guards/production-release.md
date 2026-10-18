> 当前生产状态：按用户R13要求已恢复10月18日f6dbe的改写逻辑与旧PDF。V6及其各阶段验收留作历史，当前以[完整回退记录](../../../docs/releases/cn-resume-user-rollback-20261019.1.md)为准。

# 国服简历优化稳定性发布规范（当前V6）

用户授权继续优化、自测通过后上线。本轮仅CN Backend；真实六例质量、正式保护切换、独立verify与实际180秒观察均通过。此前v4/v5候选失败并停止，其全部marker与结果保留，不得部署；[v4旧规范](production-release-v4-history.md)仅作历史。

实际父/回退image `sha256:6f9a55d8503971265e88dd97a8db804a0b3a7d8a785dc14320fc7fb54b3e443f`，旧容器2a907032…；Web88ae70/2124eee8…及其它6组件均非目标。新鲜baseline SHA `013f0b4586266ab681cc6f9d6d48c98647cc1d5bff8f65ef9056de21b7ab4cf3` 绑定完整231源、202完整schema、340有效Settings、315静态/NGINX、全部Config/HostConfig/完整Mounts/网络/归属与7非目标。只允许以下12源，231→241，原229输入保持。无配置/依赖/DDL/费用/Web/Global/助手/模拟面试/Git变化。

| 源 | SHA-256 |
| --- | --- |
| ai/prompts/resume-optimizer/review.zh-CN.v3.md | c18ed5e8544f85de1981382f14532dee73e41ddad7d4b1f01ba8b95d8031de06 |
| ai/prompts/resume-optimizer/review.zh-CN.v4.md | 3c71da05bc4c46227e27a96fea4b557b8965f6b768edb6cb3b21f21b948f9bbf |
| ai/prompts/resume-optimizer/review.zh-CN.v5.md | c99ecc7b5e2f56fe2b7be97bc237db7b0e913c01067ee0fed106fcaf227ea0ee |
| ai/prompts/resume-optimizer/review.zh-CN.v6.md | fcd308f6ebf21c3d42b3bfcc23a1a9a56b8696b9f7f249f17c85207d5bae01bc |
| apps/backend/app/schemas/cn_resume_optimizer_provider_v3.py | 2ce9dbaaf32488e5a333c6f85b03bd0bf123fa77006ee4ae83ee2c979c761e75 |
| apps/backend/app/schemas/cn_resume_optimizer_provider_v5.py | 9a1013eba99fcd9ddcc4677a8e035f7c9c898ce162a9cd709fa5fd49587d2d0e |
| apps/backend/app/schemas/cn_resume_optimizer_provider_v6.py | 06a0df03075906ed2f978a78892b6d0bdbf7ebc4237c3a33387a6ac213c9bb6a |
| apps/backend/app/services/cn_resume_optimizer_anchors.py | 93f5dee46a5e9fe85f0f5f7ac565af6e62521e24bc3d293bd4f681d0e7f80c50 |
| apps/backend/app/services/cn_resume_optimizer_provider.py | 2d1c8d45c393ecea21ea4e12006d56c75449e7375a31f6188c7877a60da6b94b |
| apps/backend/app/services/cn_resume_optimizer_responsibility.py | ccc9629dde987d2e7ba3e2b1f5f234a9ba080e220515a20055707f5feccf970f |
| apps/backend/app/services/cn_resume_optimizer_service.py | 82d43d5262428ae71da9fef223ceef3dd8a37b560799d4839c03d300787bfbfc |
| apps/backend/app/services/cn_resume_optimizer_units.py | 4762a6f4e32e15a6cb52a603b969f92b6ae7456da0f2542940aedd52029c6407 |

固定已验收候选 `sha256:8c9aaeb46cf7f1cd9d41c886f5407070bb6bb30f16fb2df0cb32d0ddee96fa8b` 从实际父digest派生；53个原发布保护函数AST保持，只改prepare/check_inputs/probe/最小service差异验证。正式prepare只引用该既有不可变QA镜像，创建本轮专属tag，不另build。服务旧4caa→82d4只新增fresh任务promptVersion传参，默认商务PDF/Word/金融/取消/修订等保持。

本地当前833/833，0失败/错误/跳过；QA工具26例和发布工具104例通过，均与模型质量分开。实际六个固定合成case各1调用，全部产生安全实质修改；前两失败阶段4+1请求保留，本任务共11次、重试0。连接中断经marker不存在、排他锁空闲与原服务健康证明发生于第三例模型边界之前，未消费模型请求，旧连接失败记录保留。当前接口为prompt_json，不能宣称API强制JSONSchema；新具名评分仍严格服务端校验，不填假分。

实际候选多次禁网只读探针241源/202schema/340Settings/七副作用0、原10PDF同字节14页/Word部件/双get守卫及Linux单root只读挂载均通过。实际quality verify完整6/6、生产业务写入0，acceptance已按原始receipt绑定。有限合成样本不能冒称长期真实用户成功率。

正式根 `/opt/offersteady/releases/20261019-cn-resume-stability-1`，39文件payload精确SHA/不含符号链接，控制器SHA `d5d4fb233c8371a83d43702fc956e1b665fdc7020822960b885a9c2178c6399d`、input SHA `5cccdaab1ec4135cdcba0aee5554c48210c6c70924c83372d0e2e0995ad559bb`。完整acceptance SHA `e5b05e7e1b2f0c5210c62374dffed16aa042b0057309da7ca4474d4577069b57`。控制器及每项支持文件双向绑定，额外/缺失/漂移拒绝。私有配置/Compose/原日志只留服务器根0700、私有文件0600；不移动共享tag或改启动/挂载/端口/停止策略。

正式发布必须完整复用[既有保护规范](../add-cn-resume-delivery-template/production-release.md)第3–5节：排他锁、实际归属/全配置/完整Mounts/非目标、image-only overlay、原完整七门禁、临近实际TCP8000/netns前后绑定及固定旧digest受保护恢复。preflight和临近cutover各重新核完整基线与七门禁，不复用旧快照。busy只保持服务等待，unknown/readfail/漂移停止；绝不结束用户、清活动/租约或放宽TTL。正常切换必须Running且实际TCP读数0；仅本次精确归属candidate已知exited冷启动失败且完整双inspect停态证明时，恢复才可用明确stoppedProcessProof，不能伪装读到0socket。原StopTimeout null/无显式graceful参数保持；门禁降低风险但不保证绝对无竞态。

只对精确归属且已知可恢复健康/公共验收失败，在所有同样保护重新通过时恢复原6f9；未知/恢复失败停止报告，不删任务/新稿/账本、不重放用户。若已经部署则按真实归属和结果verify，不重复重启。Backend IP实际变化才可沿用原NGINX检查/reload刷新DNS，不改配置或发布Web/Admin。

部署后核实际新容器/上述候选healthy/restart0、241源/202schema/340Settings/315静态/NGINX/7非目标/共享tag全保持，9公共检查覆盖七入口200和匿名能力/导出401/private,no-store。仅脱敏ERROR/traceback/5xx/固定诊断聚合，记录真实180秒窗口及4000行上限是否截断。只有实际deploy/verify/观察通过才通知用户测试，不代登录/读用户简历/调生产模型/建业务job/压测。证据在artifacts/cn-resume-responsibility-20261019/v6/。

实际完成：新Backend容器2ccf5216ce9c32d9f35a96c788649ead00c126d66767930cbceac41ca1e8638d / 本文8c9候选，上海2026-10-19 04:17。deploy/verify各9公共检查通过，真实完整241/202/340/315/7非目标保持。最终观察1792354656835–1792354836835共180秒、346行/4000未截断，目标healthy/running/restart0，ERROR/traceback/HTTP5xx及固定/未知诊断均0。无busy/恢复/失败/reload/Git。部署门禁与最终观察为实际证据，受保护恢复等未触发分支只由104工具回归覆盖。


## User-directed quality rollback (R13 overrides v6 production target)

2026-10-19用户反馈最终输出不整齐、不如昨天，明确要求“改写逻辑和 PDF 模板都恢复到昨天”。本轮不继续修改AI规则，按旧正式发版固定image sha256:f6dbe8fd498f1f965bf8ba611d666e7ea49475ac1a7bf01b547ed79e8c6bbfaa恢复v2改写与旧shared PDF排版。今天v6合成调用/安全通过不代表用户认可最终整体可读性，旧验收和失败均留历史，不能以其阻止本次已授权回退。

新鲜只读实际基线为2ccf5216/8c9、241输入，SHA718f4783545b229cd6dcedd77cd7e68bbb2c5c804d68d07628a1f38d9a00add4。目标是10月18日最后正式Backend f6dbe的230完整输入：撤回13路径变化（11新增不再在目标镜像、2旧文件恢复），原228输入保持。202完整schema/340有效Settings/315Web静态/7非目标/费用/模拟面试保持。无应用源码实现/构建/模型/DDL/数据恢复/Git，不删除今天的用户资料、优化任务/已保存稿或账本，不重放历史任务、不自动把旧结果重新优化；新任务恢复v2，已完成v6结果按相同public wire读取和旧PDF导出，需纯合成禁网验证。

该行为为用户明确选择的产品质量回退，不属于无依据自动故障恢复；使用新独立发布根/计划/真实基线，不篡改旧prepared/progress或覆盖旧控制器。新控制器仅调整输入/prepare/镜像probe/verify_current，原53完整归属/配置/Mounts/image-only切换、重复七门禁、真实TCP/netns、未知停止及严格停态恢复保护函数AST保持。使用当时已发布固定不可变镜像，不从旧目录重建；核对原Config与目标是当前镜像实际祖先，探针230完整源/202schema/340配置、真实合成Word/PDF/新旧已存稿兼容、七副作用0。新的known健康失败仍只在相同保护下恢复本次冻结8c基线；漂移/未知停止。正常user回退必须当前Running/healthy并实际TCP0，忙碌等待真实用户结束、不清活动/放宽门禁。

服务器根/证据：/opt/offersteady/releases/20261019-cn-resume-rollback-1；artifacts/cn-resume-user-rollback-20261019/。预检查与临近切换均完整七门禁+实际TCP/netns，全量功能/配置/Web和7非目标保持；独立verify/9公共检查和实际180秒脱敏观察后才报告恢复完成。新记录明确旧v6部署已被取代，保留研发工作区且标明非线上，不能自动再次发布v6。

回退准备实际通过：15文件固定payload，controller SHA `739c7a6777b900548c9b2546e0ab7d90df312268641fee9b013f6baee014d28f`、input SHA `235319c40846e606b251aa77b545a2d1fecac31db4543d2f40d1a4b9f1f9d198`。95项工具回归；实际f6dbe禁网只读230源/202schema/340有效配置、旧真实Word/PDF、已完成v6结果读取和旧PDF service双get导出、七副作用0。当前仍待正式保护切换及独立验收，不预填成功。


R13实际完成：目标旧f6dbe，当前容器db1d63010436b4bb38060dbdc885a80db61deab3f4ebd584700fb255693185a6；完整230源/202schema/340配置/315静态与7非目标保持，9公共检查通过；最终观察1792356543491–1792356723491共180秒/394行，4000行上限未截断，同一目标healthy/running/restart0，ERROR/traceback/HTTP5xx及固定/未知失败诊断全0。没有恢复/代理reload/新模型调用/业务测试数据或Git操作。用户数据和已保存稿不回填，新任务与后续PDF下载使用旧版本。证据为artifacts/cn-resume-user-rollback-20261019/，包括root-final-rollback-review.json；双根strict及链接校验在最终收尾执行。
