# Global auth/state parity verification

本记录按 [鉴权规范](specs/global-authoritative-auth-parity/spec.md)、[状态规范](specs/global-fresh-state-read-parity/spec.md)和[发布规范](specs/global-auth-state-protected-release/spec.md)逐场景核对。**已于北京时间2026-10-17 04:49:52.693完成Global Backend切换，独立verify、公开前后对照与97.93秒短时观察通过，交付状态deployed_verified。** 真实P95/供应商/物理设备效果没有在本轮测量；条件故障和回退分支仅为合成验证。

## Evidence and source boundary

证据根目录为本地 `artifacts/global-auth-state-20261017/`；这些保存的本地文件不作为干净克隆中必然存在的链接。

- E1：`baseline-binding.json`、`runtime-before.json`。实际重读镜像 `b31a810a…` / 容器 `c2b7caa3…`，healthy、restart 0；236 个 app/Prompt 哈希与保存源一致；实际完整 215 个 HTTP 路径及 OpenAPI SHA `e8c83de8433c7a5c39a86cbe9bd343d5d4998e8f733e1e7ae00abf50009a17e1`，5 Compose、1 Env、6 个非目标组件已记录。完整私有配置/原镜像冻结仍在生产准备步骤核对。
- E2：`candidate-proof.json`、`routing-proof.json`。仅八文件改变，另外 228 文件保持；253 个非批准方法逐字保持，所有未批准 AST 相等；Global 内存构造的原字段和八个 GET 原正文/签名/装饰器保留。74 个 Prompt、Global web billing、账号/语言/商业源、预取三个文件均保护。独立复核再次执行哈希、方法字节、剩余 AST 及八入口声明对比通过。离线业务 shell 为 151 路径，其 schema 与完整实际 main 分开，不能代替 215 路径的运行检查。
- E3：`verification/candidate-auth-state.json` / XML，112 项通过；`candidate-auth-state-global-postgres.json` / XML，4 项通过。包括每请求 SQL/连接/写行计数、60 秒边界/竞争、Global 账号/密码/邮件/语言、资料与 ASGI 状态合同。Global PostgreSQL 补充覆盖当前 profile/bindings/默认语言、改密保留本设备/撤销其它设备、重置/刷新/退出及陈旧 touch。
- E4：`verification/candidate-regional.json` / XML，70 项通过。覆盖实际 Global usage adapter、会员/模拟准入、语言路由、英文回答、产品区域、Creem commerce/checkout。
- E5：`verification/candidate-control-prefetch.json` / XML，109 项通过；`candidate-control-prefetch-global-compatibility.json` / XML，22 项通过、另 16 个 unittest subtests。后者使用已验证 Global helper/fixture 适配，不能把 38 个 JUnit testcase 又与 16 个 subtest 重复相加。
- E6：`verification/candidate-storage-qualified.json` / XML，44 项通过；`candidate-auth-state-foundation-qualified.json` / XML，7 项通过。包含实际 Global PostgreSQL/mock API/换轮/轻心跳/Redis 恢复及会话、资料、复盘、设备/runtime 合同。以上 E3–E6 限定合格集合合计 368 项通过、另 16 个 subtests；不宣称全仓库全绿。
- E7：`verification/release-support.xml`，273 项通过、零失败/错误/跳过，包含发布控制/门禁/probe 与 tamper/IO guard 分支。[控制器](../../../scripts/release_global_auth_state.py) SHA `23fc21a6249ab201fc688393a6ef73172037dcf91061d4e591afbf3a7395f783`；probe SHA `c94b88852425e04af2a56484332c336d66222fda56ca464137bd02e6a76f0710`。独立审查没有未解决 P1/P2。恢复在冻结原镜像/环境/网络独立执行只读门禁，不要求坏候选健康/import/Env 可用。
- E8：`public-and-gates-before.json`。五项权威门禁全部受保护计数为零，未知/失败计数为零；五个匿名入口返回 200：health、login、会员目录、mock capabilities 和 Web 标识；实际配置及公开 mock enabled 均为 false。此为发布前快照，不是临近切换两轮门禁或发布后证明。
- E9：`production-status.json` 与 `production-preflight.json`，两者退出 0。实际候选固定镜像 `sha256:c0503cb8a166dc4cfb64e3d4ca1f98792e788cdb29147d8282a8e43d0146726a`，原镜像仍为 `b31a810a…`；5 Compose/1 Env/6 非目标和有效配置 SHA `fd56081071dcad5b9a6933d31fab72919c07a88f335fd688117531e5f565338d` 冻结。实际镜像隔离 probe 通过：162 app/74 Prompt、253 保护节点、151 shell 路径、2 mock WebSocket、8 同步入口、Global mock false/政策/助手1.3.5保持；DB/网络/写入/线程启动/生命周期均零。preflight 五门禁全零、`productionChanged=false`；不能代替正式 deploy 的重复门禁及发布后检查。
- E10：`production-deploy.json` 与 `production-verify.json` 均退出0，实际镜像/容器为 `c0503cb8…` / `e82bbc37821cc6f72112b66593f5492b6f5276f331245e2e703aae97bc2842e3`、healthy、重启0；deploy记录临近两轮各五门禁均通过且所有受保护/未知/错误/陈旧例外计数为零。162 app/74 Prompt、完整215路径/schema、环境/有效配置/模型、共享标签和6非目标保护均通过，未重载代理。`public-and-gates-after.json` 与 `public-comparison.json` 确认五入口200、mock false、会员目录/mock能力/Web构建三项dataSha及login body前后一致。尚不包含短时日志观察或真实用户体验验收。
- E11：`production-short-observation.json`在容器启动97.93秒时确认running/healthy、重启0、6非目标身份不变；结构化ERROR或CRITICAL、traceback与HTTP5xx计数均0，仅聚合、不导出原始日志。`final-delivery.json`状态为deployed_verified，明确Backend only、CN未改、无Git提交/推送、没有触发真实回退和真实模型/物理设备验收；该短窗口不代表长期稳定性或真实P95改善。
- E12：`candidate-verification.json` SHA `dd6e3101d72a9ecf0b9a5536cff1c683d9acaec896edae436a65ba2c8e4299b3`最终绑定368项+16subtests/0跳过、八文件测试后冻结、七组限定通过记录与既有差异。`benchmark-auth.json`含实际Global原/候选串行与8并发、窗口内与touch到期各100次，共800调用/0失败；窗口内连接400→100、SELECT300→100、写行100→0；touch到期候选串行101连接/1更新、8并发108连接/8尝试但只1行实际更新。不是生产负载或P95证明，不重复计为pytest。

## Scenario matrix

| 能力 / 场景 | 已核对证据和状态 |
| --- | --- |
| Auth：Repeated valid requests use consolidated authority | E3：逐请求读取、一连接/SELECT、窗口内零写和身份结果通过。 |
| Auth：Authentication state changes before the next request | E3：撤销/删除/封禁/到期及刷新/改密/重置/退出生命周期通过。 |
| Auth：Invalid tokens and unavailable authority fail closed | E3：坏签名/类型/到期/缺失/owner 不匹配、仓库失败无授权副作用；E7 probe 另校验签名有效的非 access 拒绝。 |
| Auth：Concurrent due touches race in one interval | E3：真实隔离 PostgreSQL 与内存并发，实际 touch 行数至多一次，安全字段不变。 |
| Auth：Revocation deletion refresh or password reset commits first | E3：受控旧快照 touch/expiry、Global 实际 PostgreSQL 密码/刷新/退出交错通过。 |
| Auth：Global lifecycle executes against the actual source candidate | E3/E4：完整 Global 邮箱/密码/刷新/语言/商业测试通过；E2 保留未批准生命周期方法。 |
| State：Normal and expired states preserve their contracts | E3/E6：idle 五字段边界与零资料读取、调用方结束清理/异常语义通过。 |
| State：Another owner or deleted session is requested | E3：403/404、owner/删除和无资料副作用通过。 |
| State：Shared materials and absent sources appear in multiple sessions | E3：document ID 与 None 仅本次调用复用，mock 版本不刷新。 |
| State：Material changes or another owner reads later | E3：下请求 deleted/deleting/processing/index/version 变化和并发 owner 隔离通过。 |
| State：Slow state dependency does not freeze the event loop | E3：八个真实 ASGI 状态入口阻塞时 sentinel 推进、错误/取消及后续恢复通过；不是池饱和保证。 |
| State：Regional response and existing optimizations are regressed | E2/E3/E5/E6：Global 原正文/语言/billing、heartbeat/ACK/控制/预取/清理受保护并回归通过。 |
| Release：Actual runtime differs from a historical release or development tree | E1/E2：本次实际基线已重核并逐节点迁移；E7 漂移拒绝合成通过，未在生产制造漂移。 |
| Release：Global source and policy protection are checked | E2/E4/E8/E9/E10：Global 政策/语言/Prompt/未批准源保护；实际候选及上线probe/公开mock false、目录与Web标识前后对照均通过。 |
| Release：A hidden full-app route or schema drifts | E1冻结完整215路径/schema；E7漂移拒绝合成通过；E9/E10实际切换前后完整main重核同一schema通过。未在生产制造路由故障。 |
| Release：Candidate or synthetic validation fails | E7：273 项含候选源/Prompt/节点/预取/同步节点/路由/schema/config tamper 拒绝及 IO guard；E9 实际候选镜像离线 probe 通过，故真实失败阻断未触发。 |
| Release：Protected or indeterminate activity is observed | E7：非零/缺失/异常/未知/不确定及第二轮新活动阻断合成通过；E8 当时空闲。未声称生产已触发阻断。 |
| Release：Immediate gates and identity checks pass | E10：临近正式切换两轮各五门禁全零、身份复核与实际仅Global Backend切换通过；6非目标及配置/共享标签保持。 |
| Release：Candidate health or environment fails after cutover | E7：冻结基线独立恢复门禁、故障候选health/Env不作恢复前提、仅本次Backend恢复合成通过；E10真实发布成功，未触发真实回滚。 |
| Release：Later deployment or new work prevents recovery | E7：外来容器/后续发布/配置或恢复私有上下文漂移/新活动拒绝合成通过；未制造生产冲突。 |
| Release：Checks pass without real-user load or hardware testing | E10/E11：独立verify、公开前后对照和97.93秒聚合观察通过，final-delivery为deployed_verified；无真实P95、实体收音或模型效果证明，不把成功部署当作体验改善实测。 |

## Existing differences and limits

七项共享工作区断言在未改动的实际 Global 源上均复现：五项 CN 专有 cleanup API/字段、一项旧设备绑定结束方式、一项依赖尚未在 Global 实际源出现的 CN duration property。证据为 `baseline-control-prefetch-known-cn-cleanup-differences.json`、`baseline-auth-state-foundation-device-baseline-difference.json` 和 `baseline-storage-known-cn-interface-difference.json`。限定集合显式排除它们；Global 原无截止行为另由实际模拟运行/报价合成测试验证，没有迁移 CN 属性以追全仓绿。

Global PostgreSQL 初次补充测试误把改密返回值当作 UserRecord，已按实际 void 合同修正测试断言；源未改。测试专用 ACK/预取 helper 适配见 `verification/test-support-adaptations.json`，声明保留原断言。probe 初次合成 AuthenticationService 缺 password hasher，在 Global 构造失败；仅探针增加合成 PBKDF2PasswordHasher 与 1,000 次合成迭代，随后 E7 十项 probe/guard 测试及 E9 实际隔离候选镜像通过，产品八文件不变。旧 `local-probe-rehearsal.json` 初次失败记录保留，最终真实镜像结果以 E9 为准。

测试只允许本地 `127.0.0.1:55445` / `127.0.0.1:56385` 合成存储，没有复制真实用户数据/调用供应商。SQL计数和ASGI sentinel证明指定冗余及阻塞风险降低；没有量出Global真实网络/排队/供应商时间或整体API P95。源候选回归本身不替代生产验收；实际准备/切换/独立verify、公开对照与短时观察见E9–E11，实际Global合成计数见E12；真实用户与实体设备验收仍属未执行限制。
