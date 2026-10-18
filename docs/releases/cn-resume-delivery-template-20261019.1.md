> 当前状态：已被[用户要求的完整回退](cn-resume-user-rollback-20261019.1.md)取代，下文为当时发布历史，当前国服使用10月18日f6dbe版本。

# 国服商务简历 PDF 模板 20261019.1 发布记录

状态：国服Backend已于上海2026-10-19 00:52:37切换，实际deploy、独立verify、180秒观察与最终独立上线审查通过；root最后双根strict/链接收尾通过，任务16/16。依据[生产规范](../../openspec/changes/add-cn-resume-delivery-template/production-release.md)、[验收](../../openspec/changes/add-cn-resume-delivery-template/verification.md)；[首轮本地记录](cn-resume-delivery-template-local-20261018.1.md)与[商务版本地记录](cn-resume-delivery-template-local-20261018.2.md)保持历史。

本次仅使原简历优化PDF下载使用商务深蓝单栏A4模板：抬头、栏目、经历层级及自然分页更清楚，导出仍只排版当前已保存稿，真实文字/完整原序/事实确认和前后两次权限/修订守卫保持。原DOCX不变；没有新增AI改写或消费。会员每日3次免费/其余100积分、模拟/普通/笔试、Web/Global/助手、Prompt/数据库/环境/依赖/字体均未改，不操作Git。

实际基线`current-baseline.json` SHA `007c9fddb42158eb214be28ceac2e2922a89552d38ad67a44c9d0c606d4c63b5`绑定旧Backend50bcb/f6dbe、Web88ae/2124及230输入/202完整schema/340Settings/315静态。发布产品源只新增CN renderer SHA `76925432e1c8c7ac7801e8cc4978fba67641af65f8c1a7e748bf0593fc0f523d`与CN service默认PDF分发 SHA `4caa2319066a654320f07527dac5243d0431b7382a57a8e1e1d4d0dbba0e2d66`，其他229原输入保持，230→231；完整service AST归一后与实际旧源一致。Web作为第7非目标冻结，不重发本地83文件标准build或修改线上build标识。

服务器目录`/opt/offersteady/releases/20261019-cn-resume-template-1`。final-2 controller SHA `0feeabe630f14c235260ab0de0a2d0b36aea43a5a42942ea34bd8a2a518325c7`，input SHA `0aa27bfb3eaac0e5a65f17bcc046215fc07217e37b0c888b71e8cb425e31a92c`；96工具回归及独立工具审核通过。实际候选`sha256:6f9a55d8503971265e88dd97a8db804a0b3a7d8a785dc14320fc7fb54b3e443f`从固定旧`sha256:f6dbe8fd498f1f965bf8ba611d666e7ea49475ac1a7bf01b547ed79e8c6bbfaa`派生，Image Config全等、92层父前缀完整/候选93层；实际禁网只读限资源探针10份14页PDF逐源SHA/文件SHA/页数与本地验收相等，原Word部件和双get等守卫通过，231/202/340及七类副作用0。独立actual-candidate-review SHA `7f5311b649dd0aec9a565e80110895b3279ae8177ef89dbf9099fc0ff8b6126d`通过，区别于本机演练。

preflight与切换临近分别完整七门禁有效空闲、实际Backend TCP8000为0且进程/netns前后绑定。只切Backend为容器`2a9070321263a2a57ecb8c3e20edef63f5bbabfc7e765062094d00a42fa25f90`/上述6f9镜像，StartedAt=`2026-10-18T16:52:37.493571389Z`。deploy与独立verify各9检查通过：7公共入口200、原HTML/build保持，匿名能力及无效合成导出路径各401/private,no-store；完整231源/202schema/340Settings/有效配置、315Web静态/NGINX、全部7非目标保持。实际无busy/defer、发布失败、恢复/回退或代理reload；恢复/未知停止等条件分支仅合成工具回归覆盖。

初始观察相同新容器running/healthy、restart0，实际覆盖启动后53.214秒/134行；最终观察再次确认相同容器/image健康、重启0，实际atMs1792342387231至1792342567231共180.0秒/406行，4000行上限未截断；两窗口ERROR/traceback/HTTP5xx/固定失败及未知诊断均0。progress/signature的starting是切换瞬间历史，不能据此推断当前健康。独立最终上线审查`independent-audit/final-release-review.json` SHA `7b98961d252b42dca56d037358038f1c3883db0b550f43fad85192419e5c17e1`通过，绑定完整部署/verify/保护与最终观察；root最终文档校验待追加。短窗口不承诺零竞态、长期P95、所有真实简历/ATS或打印设备兼容。实际原StopTimeout为null且无explicit graceful参数，七门禁+TCP只是降低瞬时切换风险。

保留本地排版修复、bddd单行碎尾、首稿探针失败及final-1工具审核纠正历史。final-1曾因缺少完整Pid/进程状态/host目标netns与exec self/init绑定在上线前被阻止；final-2仅补该证明及负例后重新冻结/独立审查，没有放宽门禁或将旧71项通过当作最终候选验收。

证据位于原仓库`artifacts/cn-resume-delivery-template-20261018-release/`（20261018为任务目录名，不是本次生产日期）：baseline/GO、final-2 freeze与独立审查、prepare/candidate-evidence/actual-candidate-summary、preflight/root-cutover-go、deploy/deployment-evidence/verify、observation-initial.json、observation-final.json及独立final-release-review.json；root最终strict/链接收尾证据待追加。不包含私有环境、socket地址或用户正文/原始日志。未代用户登录、读取真实用户简历、调用真实模型、创建生产测试job/usage/钱包/资料或压测；用户可用原简历优化页面正常账号重新下载PDF验证。
