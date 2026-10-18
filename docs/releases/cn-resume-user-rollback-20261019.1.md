# 国服简历优化回退 20261019.1

状态：国服已恢复10月18日最后正式版本，固定历史镜像切换、独立verify与180秒脱敏观察均实际通过。用户明确选择“改写逻辑和 PDF 模板都恢复到昨天”；目标为10月18日最后正式发布的[安全局部改写版](cn-resume-optimizer-safe-edits-20261018.1.md)，以[当前R13规范](../../openspec/changes/stabilize-cn-resume-responsibility-guards/specs/cn-resume-responsibility-stability/spec.md)与[保护流程](../../openspec/changes/stabilize-cn-resume-responsibility-guards/production-release.md)执行。

用户反馈今天v6成稿整体可读性不如昨天，因此按明确授权整体恢复v2改写逻辑与旧shared PDF模板。本次是用户选择的产品质量回退，不将此前6例合成调用成功/安全校验称为用户认可的完整成稿验收；不继续修改Prompt或重采样。已有用户资料、今天的任务和已保存稿、实际账本均保留，不自动重写、重新优化或退款/收费。新建任务使用v2；已有v6成稿继续可查看、编辑，并按旧PDF模板导出。现有每日会员3次免费/其余100积分、模拟/普通/笔试、Web/Global/助手/性能补丁保持。未操作Git或更改本地研发版本；本地v6研发文件仍保留作历史，不是当前线上版本。

新鲜实际基线2ccf5216/8c9的完整241源/202schema/340有效Settings/315Web静态/NGINX/7非目标，baseline SHA718f4783545b229cd6dcedd77cd7e68bbb2c5c804d68d07628a1f38d9a00add4。实际目标固定image `sha256:f6dbe8fd498f1f965bf8ba611d666e7ea49475ac1a7bf01b547ed79e8c6bbfaa`、完整230输入，原228输入逐项不变，13路径撤回（11新增不再存在于旧image、2旧文件恢复），全量API/配置/静态/非目标保持。不从旧目录重建或覆盖当前源码，不回滚数据库/资料/账本，无DDL/依赖/配置/字体/模型切换。

独立服务器根/私有配置：/opt/offersteady/releases/20261019-cn-resume-rollback-1，根0700、私有0600；15文件精确绑定，controller SHA `739c7a6777b900548c9b2546e0ab7d90df312268641fee9b013f6baee014d28f`，input SHA `235319c40846e606b251aa77b545a2d1fecac31db4543d2f40d1a4b9f1f9d198`。旧53个归属/全Config/HostConfig/完整Mounts/网络、image-only切换、七门禁、实际TCP/netns前后身份、受保护恢复函数AST保持。新控制器仅调整输入/历史镜像prepare/offline probe/目标清单verify_current；目标Config全等且RootFS是当前镜像实际祖先，只引用已存在的历史不可变image并创建本轮专属tag，不build/pull或移动共享tag。

95项合成工具回归通过。目标实际禁网只读230源/202完整schema/340有效Settings、旧v2事实/部分改写/0有效拒绝及capabilities/模拟面试权益、真实Word/PDF通过，七副作用0、不进入业务lifespan。新增纯合成已完成v6 public wire读取及service默认shared PDF实渲染/前后双get导出通过，无生产测试job/usage/资料/钱包写入或真实模型调用；没有读取真实用户简历或原始响应。目标完整源与此前正式f6dbe清单一致，未把本地代码或健康版本字符串当作部署事实。

实际于上海 `2026-10-19T04:49:20+08:00` 完成切换收据，新Backend容器 `db1d63010436b4bb38060dbdc885a80db61deab3f4ebd584700fb255693185a6`，StartedAt=`2026-10-18T20:49:00.136105221Z`。preflight和临近切换完整七门禁有效空闲，实际TCP8000读数0且Pid/netns前后绑定。仅CN Backend重建，Web/其它6组件保持，无终止用户/清理任务/改TTL。没有busy延后/切换失败或恢复，固定8c仅作为本轮已知健康失败时同样受保护的恢复基线；当前实际线上为f6dbe。原停止策略不变，瞬时保护不能保证绝对无竞态。

deploy与独立verify各9公共检查通过：健康/登录/简历/普通/模拟/笔试/build七入口200且原HTML/build不变，匿名capabilities和合成无效export401/private,no-store；完整230源/202schema/340配置/315静态/7非目标和共享tag保持。progress的starting只是切换瞬间历史，初始直接inspect同一新目标healthy/running/restart0。最终观察实际180秒/394行、4000上限未截断，同一目标healthy/running/restart0、ERROR/traceback/HTTP5xx/固定与未知诊断全0；不将短时错误统计称为长期质量/成功率或P95验证。

证据：artifacts/cn-resume-user-rollback-20261019/ 下完整新鲜baseline、15文件冻结、95工具测试、actual-target-review、actual-preflight/deploy/verify/evidence、初始及最终聚合观察和root审核。所有原发布/失败和v6研发证据留历史。新版本不改变既有已生成文本，要体验昨天的生成逻辑需要用户正常新建优化任务；原已保存稿与费用不会因本次回退被重写。


R13实际完成：目标旧f6dbe，当前容器db1d63010436b4bb38060dbdc885a80db61deab3f4ebd584700fb255693185a6；完整230源/202schema/340配置/315静态与7非目标保持，9公共检查通过；最终观察1792356543491–1792356723491共180秒/394行，4000行上限未截断，同一目标healthy/running/restart0，ERROR/traceback/HTTP5xx及固定/未知失败诊断全0。没有恢复/代理reload/新模型调用/业务测试数据或Git操作。用户数据和已保存稿不回填，新任务与后续PDF下载使用旧版本。证据为artifacts/cn-resume-user-rollback-20261019/，包括root-final-rollback-review.json；双根strict及链接校验在最终收尾执行。
