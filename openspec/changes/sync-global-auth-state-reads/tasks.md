## 1. Authorization and actual Global baseline

- [x] 1.1 确认用户已授权同步本轮优化、自测通过后部署国际服；范围仅 Global Backend 八文件批准节点，无需重复确认，保留 Global 账号/语言/商业与全部非目标组件。
- [x] 1.2 主代理已读 apply/context，重读实际 `b31a810a…` / `c2b7caa3…` healthy/restart 0；236 个全源/Prompt 哈希匹配，完整 215 HTTP/schema、5 Compose/1 Env/6 非目标已记录。`runtime-before.json` 与 `baseline-binding.json` 为本地脱敏证据；完整私有有效部署配置在 4.3 生产准备时再次冻结。
- [x] 1.3 冻结基线与八文件批准节点，74 Prompt/253 未批准方法及区域账号/语言/Creem/预取/heartbeat/ACK/助手均保护；实际 Global 七天购买准入/UTC 三场/无 CN 积分及 60 分钟截止通过合成验证，发布前实际和公开 mock false 已重读。

## 2. Minimal parity candidate

- [x] 2.1 在实际 Global 源迁移逐请求单 SELECT 鉴权、60 秒元数据限频、touch/expiry CAS 和 access 类型拒绝；保留错误优先级、schema 兼容、内存扩展和全部专有方法/字段。
- [x] 2.2 迁移 idle 五字段投影、list 请求内 document ID/None memo 和八个同步 GET 声明；保留 Global 函数正文、签名/装饰器、mock 版本和既有执行器/缓存边界。
- [x] 2.3 全源恰八文件改变/228 文件保持，253 个未批准方法逐字及其它未批准 AST 相等，八 GET 仅声明变更、Global 原内存字段全部保留；`candidate-proof.json` / `routing-proof.json` 和独立逐项复核通过，未整文件覆盖。

## 3. Synthetic verification and independent review

- [x] 3.1 隔离本地 PostgreSQL/内存验证逐请求 SQL/连接/实际写行、60 秒与并发、安全 CAS；`candidate-auth-state` 112 项、补充 Global 实际 PostgreSQL 4 项通过（包含重复范围不能再与其中专项相加）。
- [x] 3.2 实际 Global 密码/邮件/刷新/改密/重置/退出/默认语言及 Creem/会员/mock UTC/语言路由通过；区域专项 70 项，补充 PostgreSQL 显式验证改密/重置/刷新保留语言与 profile/bindings。
- [x] 3.3 资料/idle/八路 ASGI sentinel/错误/取消与响应专项通过，另 7 项既有会话/复盘/设备/runtime 合同通过；公开五入口发布前均 200、mock false，未改旧运行错误或区域正文以适配测试。
- [x] 3.4 既有控制/预取等 109 项、Global 兼容 22 项另 16 subtests、存储/轻心跳/mock 等 44 项通过。E3–E6 合格集合合计 368 项另 16 subtests，七项旧工作区/实际源差异在未改基线复现并显式排除；独立源码/控制器审查无 P1/P2，详情及边界见 [场景矩阵](verification.md)。

## 4. Protected release preparation

- [x] 4.1 Global 控制器/五门禁/probe 已准备，分别保护151业务shell与215实际main/schema；控制器 SHA `23fc21a6249ab201fc688393a6ef73172037dcf91061d4e591afbf3a7395f783`，未套用 CN195。
- [x] 4.2 `verification/release-support.xml` 共273项通过（135控制器/128门禁/10probe），覆盖未知/活动、完整路由/配置/归属漂移与独立冻结基线恢复；无未解决P1/P2。probe初次合成hasher缺失已仅在探针修正，产品源码不变，真实候选镜像probe仍归4.3。
- [x] 4.3 实际生产 prepare/status exit 0；冻结原 `b31a810a…` 镜像、5 Compose/1 Env/6 非目标及有效配置 `fd560810…`，只叠加八文件构建固定候选 `sha256:c0503cb8a166dc4cfb64e3d4ca1f98792e788cdb29147d8282a8e43d0146726a`。实际 network-none/readonly 镜像 probe 通过，162 app/74 Prompt/253保护节点/151业务shell/8同步入口、Global mock false/政策/助手1.3.5保持，DB/网络/写入/线程/lifecycle均0；证据 `production-status.json`。`production-preflight.json` 五门禁全0/productionChanged false，正式切换仍待5.*。

## 5. Global Backend rollout and acceptance

- [x] 5.1 `production-deploy.json` exit 0，临近切换连续两轮各5项门禁全部通过，保护活动/未知/读取失败/陈旧任务例外计数均0；身份与冻结候选复核通过，没有结束面试或清记录制造空闲。
- [x] 5.2 北京时间2026-10-17 04:49:52.693仅Global Backend切到固定镜像 `c0503cb8…`，新容器 `e82bbc37…`；真实deploy与独立verify均确认环境/有效配置/模型、完整215路径/schema、6非目标与共享标签保持，`proxyReloaded=[]`。公开前后3项dataSha和login body保持、五入口200、mock false。
- [x] 5.3 `production-verify.json` exit0，候选镜像/容器healthy/重启0，236源/Prompt、完整215路径/schema、有效模型/配置/环境与6非目标身份保持；5匿名入口200、三dataSha及login body保持，mock false。`production-short-observation.json`启动97.93秒running/healthy/重启0，ERROR或CRITICAL/traceback/HTTP5xx均0、6非目标不变，仅导出聚合无rawlogs。
- [x] 5.4 本次真实发布及独立verify均成功，未触发生产回退。归属/后续发布/独立冻结基线活动门禁和安全恢复分支仅经273项support中的合成验证，未表述为真实生产故障或回退演练；固定原Global镜像/配置仍为回退基线。
- [x] 5.5 `final-delivery.json`为deployed_verified；[21场景矩阵](verification.md)、[生产记录](../../../docs/releases/global-auth-state-20261017.1.md)和[本地验收](../../../docs/releases/global-auth-state-local-20261017.1.md)记录368项+16subtests、273发布检查、800次合成调用及真实发布/观察结果，七项旧差异与未触发真实回退明确披露。真实P95/供应商/物理设备未验收，不承诺已改善；新变更与两份文档链接/diff/strict通过，CN/其它组件未改，无Git提交/推送。
