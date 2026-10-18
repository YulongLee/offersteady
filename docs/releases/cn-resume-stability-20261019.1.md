> 当前状态：已被[用户要求的完整回退](cn-resume-user-rollback-20261019.1.md)取代，下文为当时发布历史，当前国服使用10月18日f6dbe版本。

# 国服简历优化稳定性 20261019.1 发布记录

状态：国服已上线，实际切换、独立verify与180秒观察全部通过；双根文档校验收尾留证。用户授权继续优化、自测通过后上线。依据[当前生产规范](../../openspec/changes/stabilize-cn-resume-responsibility-guards/production-release.md)与[逐项验收](../../openspec/changes/stabilize-cn-resume-responsibility-guards/verification.md)。本轮仅CN Backend，不操作Git。

针对模型原文引用定位不可靠、整体片段改写可能破坏列表/表格排版、评分维度格式不稳定及窄第三方称谓误判：新v6使用服务器编号来源和短正文单元，保留原完整来源用于依据，按可信位置嵌回修改并复核对应行/格及最终稿；具名四/五维度完整类型验证后恢复原公开评分数组，不补假分或返回原文冒充优化成功。真正责任/数字/机构/技能/否定等事实校验与零有效失败退款继续生效。历史v1–v5路径各保持原Prompt/验证，不回填旧结果。

当前配置的自定义网关为prompt_json，服务器严格验证结构；未更换模型/endpoint/配置，不宣称API强制JSONSchema。仅v6温度0，原90秒/6500输出/256KiB/单次Provider与并发预算保持。收费仍为时间会员每天3次免费、其余100积分；已有深蓝A4商务PDF及原Word、编辑/事实确认/删除取消/修订和导出双get守卫保持。普通/模拟/笔试/Web/Global/伴随程序和鉴权性能补丁未发布新版本。

本地833/833、0失败/错误/跳过；QA工具26例、正式发布工具最终104例通过，不与历史重叠用例相加。固定6个合成简历真实调用各一次、6/6交付实质安全改稿，包含CRLF/引用列表、表格JD、技术术语、运营等；实际模型耗时8583–17660ms不代表端到端生产耗时。前两阶段候选失败后即停（4+1次），旧失败marker/镜像保留，不计为通过；当前阶段6次，本任务共11次<=12、无模型重试。一次SSH中断经锁空闲/第三例无marker与原服务健康证明位于模型调用前，连接错误保留，未消耗额外模型请求。无读取真实用户简历/OSS或生产测试job/usage/钱包/资料写入。

实际父/固定回退image6f9a55d8…、旧Backend2a907032…；新候选 `sha256:8c9aaeb46cf7f1cd9d41c886f5407070bb6bb30f16fb2df0cb32d0ddee96fa8b`。新鲜基线SHA013f0b45…绑定完整231源/202schema/340有效Settings/315Web静态/NGINX及7非目标。精确12文件增量（原2文件变更/新增10），原229输入逐SHA保持，231→241；新service相对实际旧源仅fresh payload promptVersion传参，默认PDF分发不变。候选Image Config相同/父RootFS前缀保持，已验收同一QA镜像用于正式prepare，不另建未测候选。

正式根/专属固定镜像overlay：/opt/offersteady/releases/20261019-cn-resume-stability-1。控制器SHA `d5d4fb233c8371a83d43702fc956e1b665fdc7020822960b885a9c2178c6399d`；input SHA `5cccdaab1ec4135cdcba0aee5554c48210c6c70924c83372d0e2e0995ad559bb`；39文件支持/输入精确冻结，53原保护函数AST保持。私有环境和Compose原文/日志仅留服务器根0700和文件0600。actual禁网只读探针241/202/340、七副作用0、不进lifespan，原10PDF共14页文件SHA相同、Word部件/双get和Linux单root只读挂载通过。

实际于上海 `2026-10-19T04:17:54+08:00` 完成deploy收据，新容器 `2ccf5216ce9c32d9f35a96c788649ead00c126d66767930cbceac41ca1e8638d`，StartedAt `2026-10-18T20:17:33.409656331Z`。preflight和临近切换原完整七门禁有效空闲，实际TCP8000读数0/前后Pid与netns绑定。只切CN Backend固定candidate，配置/完整Mounts/网络/非目标/共享tag保持；无busy延后、切换失败、回退或代理reload。旧StopTimeout null/无explicit graceful参数不变；保护是瞬时快照，不承诺绝对无竞态。

部署与独立verify各9检查：七健康/登录/简历/普通/模拟/笔试/build入口200且原Web HTML/build保持，匿名capabilities及合成无效export路径401/private,no-store。完整241源/202schema/340Settings、315静态/NGINX/7非目标核对通过。progress中starting只是切换瞬间历史，之后直接inspect确认同一目标healthy/running、restart0。初始脱敏观察覆盖38.089秒/86行，ERROR/traceback/HTTP5xx/固定与未知失败诊断均0；最终观察1792354656835–1792354836835实际180秒、346行，4000行上限未截断；同一目标healthy/running、restart0，ERROR/traceback/HTTP5xx/固定失败与未知诊断全部0。

证据：artifacts/cn-resume-responsibility-20261019/v6/，包含当前源/本地PG回归、固定QA receipts/markers、release/release-acceptance.json、root-payload-verification.json、actual-prepare/preflight/deploy/verify.json、actual-deployment-evidence.json、observation-initial.json与后续最终观察/root审核。无原始模型响应、用户正文/标识、socket地址或私有配置离服。有限合成样本及短时窗口不能推断长期生产成功率、P95或所有简历/ATS兼容。

最终原始证据中signature.health=starting为切换瞬间历史，不是当前状态。上线最终核对由root源码审阅+已执行833/26/104测试和实际生产证据完成，本轮未使用或声称独立子代理审核。最终manifest/输入均未变，真实用户场景后续由用户自行正常测试；不将观察零错误冒称所有真实任务零失败。
