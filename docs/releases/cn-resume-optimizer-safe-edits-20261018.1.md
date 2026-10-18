# 国服简历优化安全局部改写 20261018.1 发布记录

状态：2026-10-18国服Backend/Web已发布，独立verify、完整运行快照及短时观察通过。52/52任务、81场景完成；[生产规范](../../openspec/changes/add-cn-resume-optimizer/safe-edit-production-release.md)及[本地验收](cn-resume-optimizer-local-20261018.4.md)历史保持。

本次上线安全局部改写、无有效修改失败退款、CN v2 Prompt、固定中文失败原因和AI初稿计数。会员每日3次免费/其余100积分、原金融/事实/删除/claim/cancel及模拟/普通/笔试功能保持。仅Backend3源/Web15patch，正式build标识cn-resume-optimizer-safe-edits-20261018.1；无DDL/环境/费用/额外模型/Git/Global/助手/Admin重建。

实际服务器目录`/opt/offersteady/releases/20261018-cn-resume-safe-edits-3`，控制器SHA `c6dce7b3385064dc3b4e3384be1b346553cbafa329c8e318234006db741ca62f`，输入SHA `9aa65c2d7e0ed3b975183c1ca54f2afedde4960cdc5bae5c87cb2a2733100155`。Backend容器50bcb76f…/固定镜像f6dbe8fd…，Web88ae70c9…/2124eee8…；deploy/verify/只读快照归属一致，Backend healthy、两目标重启0。

实际候选通过230源/202完整schema/340Settings/真实DOCXPDF/七副作用0、305旧静态保留至315/NGINX、306原及316候选精确模式、25项隔离HTTP/SHA及严格清理。115工具回归通过。完整七门禁空闲后Backend→Web切换；实际6非目标与共享tag保持。两次线上各19验收：17个200（含10新资源SHA）和2匿名401/private,no-store。

短时观察Backend114.289秒404行、Web79.385秒179行，未截断，ERROR/traceback/HTTP5xx/固定失败及未知诊断均0。实际未发生busy、部分恢复、回退或代理reload；条件分支由合成工具测试覆盖。未创建真实生产测试任务或钱包/资料测试写入，未重放用户任务；不代表完整180秒、长期P95或所有真实简历成功，用户可正常账号验证。

两次prepare停止证据保持：dir1过严模式probe未考虑8个原AppleDouble元数据0755的精确继承；dir2因internal网络publish为空在HTTP前停止，两次均未切线上。最终仅修模式probe及隔离私有IP传输，不chmod旧资产、不改产品/增加模型，dir3重新完整验收。

证据在原仓库`artifacts/cn-resume-optimizer-safe-edits-20261018-release/`：actual-prepare/evidence/preflight/deploy/verify/runtime/deployed-evidence/observation-v3.json、root-final-runtime-review.json及independent-audit/final-release-review.json。本地final-verification dc869f66…、三例纯合成模型各一次和旧失败/QA marker保持，不含私有配置、用户正文或原始模型响应。
