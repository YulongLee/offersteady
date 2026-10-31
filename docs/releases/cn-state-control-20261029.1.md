# 国服状态与控制查询发布 cn-state-control-20261029.1

于 **2026-10-29 00:55:05（北京时间）**完成国服Backend/Web切换与公网验收，独立再次执行verify通过。用户明确授权更新国服，并要求等没有在线面试时发布；切换前全部用户工作门禁通过。未执行Git提交/推送。

## 本次范围

合并[状态请求与资料读取优化](cn-state-read-local-20261028.1.md)和[控制查询轻量化](cn-control-db-local-20261028.2.md)两轮已自测增量。仅国服Backend/Web，连接池保持关闭。模型、Prompt、ASR/TTS、数据库schema、收费、轮询/心跳频率、worker、国际服和桌面助手保持。

初次只读核对实际Backend `sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88`，230份运行输入；实际Web `sha256:9261bdb414ae99bc16e3e7efbddef715f3ca461756ee02bc89cf2476d17b311b`，339份公开文件，均与前次发布来源一致。不得用旧封版静态包或完整本地源码构建替换实际线上资源图。

## 候选准备记录

Backend固定候选为 `sha256:3e56917daba635e780d9bd728694d823494b40a6ab67a9968c5371c1378abb3e`，从实际原镜像派生，只叠加10份已批准Python、pyproject及新增连接提供器。原镜像配置与层前缀保持；231份运行输入逐SHA核对，155份有效Python编译通过。

运行时Python 3.13.15和psycopg 3.3.5保留；固定wheel离线、禁止解析其它依赖，只新增`psycopg-pool==3.3.3`。实际发行包44份，原包版本全部等价。旧Settings逐值等价，新池配置false/4/16/3；没有修改生产环境文件。固定wheel SHA-256为`9b9cd6a4fcec47a410f7e82d408540e7f77b478509e91b44c1a5457a13e5ff37`。

实际候选在network-none/read-only环境通过探针：完整203条API Schema SHA-256保持`dd7da7440bf0177b590396cf09253219eac1b6bf786e98f9fd0ce4bcf8eee272`；合成鉴权撤销、12会话共享6资料、控制18组状态/模式/音频和owner/删除保护通过。池关闭且未激活。未进入应用lifespan，真实数据库/网络/文件写入/线程启动均0，不调用真实模型。生产私有配置只留服务器。

Web从实际339份公开文件和资源图组装，仅替换auth/Main/独立Resume三个模块中已审阅的状态读取、鉴权生命周期、初始化、mutation及显式刷新节点；其余方法和原SSE解析保持。保留全部原JS，沿反向引用闭包增加14个版本化JS。只改变4个活动HTML资源引用及版本JSON，原339份中334份逐字不变；SEO、CSS、媒体、Nginx完整输入及CSP均保持。生产仅COPY 19份增量，不使用完整本地App构建。

新增Web发布专项85项通过（实际组装模块59、实际初始化/刷新表达式7、图/字节保护19），14个新JS语法检查通过；独立审查复跑同组通过。发布控制器28项合成测试通过，与旧SEO控制器合并49项、98个subtest通过。生成器初版指令序言提取问题已改为AST提取并验证实际导入/调用；初版产物未上传。控制器补充了原容器停止但未创建候选时的固定归属恢复及回归。没有放宽旧测试断言。

本地隐藏浏览器使用禁止写入/转发的合成匿名状态，验证候选首页渲染、演示切换、套餐展示切换及登录表单。实际测试公开字节与最终产物等价；没有真实登录、面试、模型或付款测试。临时5196服务及隐藏页已关闭，用户5183预览不变。

## 真实运行结果

| 项目 | 实际值 |
| --- | --- |
| Backend镜像 | `sha256:3e56917daba635e780d9bd728694d823494b40a6ab67a9968c5371c1378abb3e` |
| Backend容器 | `437c73514248f130fc7c90474b3a2d515ecb57ef77abc264b00d1a83626c964d` |
| Web镜像 | `sha256:99822e10e7b516aefe4ad96248f9eea631d90b057cb77b8dd386cff4830516fb` |
| Web容器 | `353256013a1f83e92c846f0526e1cc5c09bdc80e0bbd42f0d8b112844478e0e0` |
| Web兼容回退镜像 | `sha256:cf644690c770dc8a69c616d527c49c838b9eef7a3a7dbf69de43ebe948a69c49` |
| 公开文件与新入口 | 353份；`assets/main-559fbe0b.js` |
| Nginx SHA-256 | `21efde0b48612b4ee3f4acb56c3b10532cfa57095adf915e2afcace79f1e8275` |
| Web发布清单 SHA-256 | `70d5fa3a7e85972013f63eba762a956fc6db0067203fe3ac66eb99ba7b4adcee` |
| 控制器 SHA-256 | `846e3af43b6be76a57bd2426f178b18aaf4159e91dc27d5c5236602cde5dd82c` |

Backend健康为healthy，Web和Backend重启计数均0。203条完整API Schema、有效配置、231份Backend输入及353份Web文件与固定候选保持。公网31项静态字节/路由/新资源验证及健康200通过；普通、模拟、笔试、简历入口保留，新JS具有正确类型及immutable缓存。六个非目标容器的ID、镜像、启动时间、重启次数与配置等签名保持。

## 用户保护与验收要求

初次检查、preflight及两个组件各自切换前，全部七项只读工作门禁及TCP8000连接门禁通过。普通/笔试/模拟面试、准备页租约、音轨/发布者、未完成回答、资料/简历任务、有效账务均受保护且为0，无未知或读取失败。不继承10月27日准备页例外，没有结束面试或清理活动。历史遗留失败任务7个和原Backend启动前的孤立回答预留22个只作原门禁的信息项，原进程启动锚点始终固定，不作清理或新例外。

已固定候选及兼容回退，冻结真实Compose、环境、有效设置与归属；只更新Backend/Web。保留全部旧静态chunks和已发布SEO，兼容回退仍保留候选新chunks。控制器通过实际镜像探针、非特权公开文件读取及离线Nginx配置检查；切换通过，无需实际回退。恢复故障场景在合成测试中验证，不冒充生产演练。

切换完成后约276秒的脱敏日志观察：Backend/Web的ERROR或CRITICAL、Traceback、HTTP5xx访问日志和stream_failed事件均0；共检查819行日志，仅导出聚合。该短窗口未进行压测，不能证明长期故障率或高峰P95改善。

两轮本地相关512项后端和662项前端通过的证据与测试限制仍见上述本地记录。既存旧foundation夹具/计时、SEO/Nginx及包体预算检查限制未在本轮修复，不能报告为全部测试通过；本地收益不能直接换算线上整体P95。发布后的实际高峰效果仍待正常用户流量观测。

[脱敏生产验收及门禁](cn-state-control-20261029.1/production-verification.json)、[Backend运行输入和依赖](cn-state-control-20261029.1/backend-runtime-manifest.json)、[Web公开清单](cn-state-control-20261029.1/web-release-manifest.json)、[实际镜像探针](cn-state-control-20261029.1/candidate-probe-result.json)、[独立审查](cn-state-control-20261029.1/independent-release-review.json)、[本地浏览器检查](cn-state-control-20261029.1/browser-local-smoke.json)、[短时脱敏错误观察](cn-state-control-20261029.1/post-release-error-summary.json)。未创建等待自动化，因为发布门禁持续通过。

生产追加规范及任务见[变更记录](../../openspec/changes/lighten-cn-control-database-access/specs/cn-state-control-production-release/spec.md)。本地脱敏证据目录为`artifacts/cn-state-control-20261029-release/`，服务器私有发布目录为`/opt/offersteady/releases/20261029-cn-state-control-1`。
