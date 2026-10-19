# 国际服鉴权与状态读取优化发布 — 2026-10-17

**2026-10-17 04:49:52.693（Asia/Shanghai）已完成 Global Backend 上线，随后独立 verify 通过。** 用户已授权开发、自测并部署国际服，国服保持现状。[本地验收](global-auth-state-local-20261017.1.md)、[需求与边界](../../openspec/changes/sync-global-auth-state-reads/proposal.md)、[逐场景验证](../../openspec/changes/sync-global-auth-state-reads/verification.md)。

## 发布范围

仅 Global Backend 八文件批准节点：逐请求单查询鉴权、使用时间 60 秒限频且带条件更新、到期处理并发保护、idle 五字段投影、列表内资料去重和八个同步 GET。减少重复数据库连接与写入，并让同步查询使用原有同步执行机制；退出、撤销、刷新、改密等安全状态仍逐请求读取。

Global 邮件/密码、默认及会话语言、Creem 和原独立会员权益保持，模拟面试仍沿用七天购买准入、UTC 每日三场、无国服积分及 60 分钟截止的原规则，开关 false 保留。所有模型、74 个 Prompt、现有问题预取、heartbeat/ACK 与三平台助手 1.3.5 保留。Web/Admin、worker、数据库/Redis、国服均不发布，不引入依赖/迁移或清理用户数据。

## 固定镜像与部署边界

| 项目 | 已核验值 |
| --- | --- |
| 实际旧 Backend 镜像/固定回退 | `sha256:b31a810a49f718e360f8ddbcbae0e7aa3d0184012b8993cd0e2f5f973bc7657a` |
| 实际旧 Backend 容器 | `c2b7caa35c86c85c13c4f9baeebb1da30465562d4ad50126c56db3d141d5bd4e` |
| 候选镜像 | `sha256:c0503cb8a166dc4cfb64e3d4ca1f98792e788cdb29147d8282a8e43d0146726a` |
| 已发布 Backend 容器 | `e82bbc37821cc6f72112b66593f5492b6f5276f331245e2e703aae97bc2842e3` |
| 候选标签 | `offersteady-global-backend:auth-state-20261017-1` |
| 回退标签 | `offersteady-global-backend:auth-state-rollback-20261017-1` |
| 服务器私有目录 | `/opt/offersteady-global/releases/20261017-global-auth-state-1` |
| 发布控制器 SHA-256 | `23fc21a6249ab201fc688393a6ef73172037dcf91061d4e591afbf3a7395f783` |

以实际运行镜像为基线，仅叠加八文件；236 个源/Prompt 文件中 228 个不变、253 个未批准方法逐字保留，其余 AST 及 Global 专有字段/正文保持。三个既有预取文件 SHA 与上轮实际镜像一致。没有使用混合 Git 源整包覆盖。

冻结实际五个 Compose、一个 Env 文件的顺序、原 project directory、完整环境和完整渲染。仅 Backend 镜像 overlay 改为固定 ID，回退只选固定旧 ID；完整配置和凭据留服务器，不导出。有效配置摘要 `fd56081071dcad5b9a6933d31fab72919c07a88f335fd688117531e5f565338d`，共享运行标签和六个非目标容器的身份均受保护。

## 验证与安全保护

实际 Global 冻结候选 368 项测试与 16 个 subtests 通过，0 skipped；273 项发布保护/门禁/实际探针测试通过。七个共享 CN 测试的既有 Global 接口差异在原基线复现并披露，合格结果不等于全仓全绿。800 次本机合成调用零失败，重复连接和写行显著减少；细节及边界见本地记录。

实际候选镜像在无网络、只读文件系统、cap-drop ALL/no-new-privileges 下通过探针：162 app/74 Prompt、253 受保护方法、八同步节点、Global 原权益/mock false/助手 1.3.5，以及 151 条离线 shell HTTP 路径和完整 schema。网络请求、DB 操作、文件写入、worker 启动均为零；未导入 app.main 或进入生命周期/依赖解析。实际完整应用独立绑定 215 HTTP 路径与完整 OpenAPI，不能用离线 shell 数量替代。

发布控制器在预检、切换邻近阶段重复五项只读活动门禁，保护普通/模拟/笔试、网页/桌面租约、音轨、回答/截图、资料任务与未知状态。任何非零或读取异常停止切换，不结束面试或清理数据。失败恢复重新确认归属和原冻结上下文，使用基线镜像、原网络和环境的独立只读门禁；不依赖故障候选，且不覆盖后续发布。控制器和支持说明见[发布脚本](../../scripts/release_global_auth_state.py)及[支持目录](../../scripts/release_support/global_auth_state_20261017/README.md)。

## 运维证据与效果边界

实际预检与切换紧邻两轮五道门禁均通过，所有受保护及未知/读取失败计数均为零；没有清理活动制造空闲。只更新 Backend，其余六个容器 ID、镜像和启动时间不变，shared tag 保留；代理地址未变化，`proxyReloaded=[]`。环境、完整配置、HostConfig 和挂载保持，运行全源 236 文件一致。

独立 verify 再次确认 running/healthy、restart 0、162 app/74 Prompt、完整 215 HTTP 方法/路径以及 OpenAPI SHA `e8c83de8433c7a5c39a86cbe9bd343d5d4998e8f733e1e7ae00abf50009a17e1` 与原运行版本相等。模型、区域设置及所有非目标身份保持。五个匿名公开检查均 200，除 health 动态外，mock 能力/会员目录/Web 标识的 data SHA 和 login body SHA 均与切换前相同，mock false 保留。

固定旧镜像及回退配置已保存；未触发生产回退，恢复分支仅做合成验证，不声称生产故障演练。

上线后截至启动 **97.93 秒**的短观察：服务 running/healthy、restart 0，六个非目标组件身份再次保持；结构化 ERROR/CRITICAL、Traceback 和 HTTP 5xx 日志计数均为零。5xx 同时解析 access 行及结构化状态字段，仅导出聚合，未导出原始用户日志。证据为 `production-short-observation.json`，不代表长期稳定性或真实 P95 结论。

脱敏证据在 `artifacts/global-auth-state-20261017/`：`production-status.json`（实际候选镜像探针）、`production-preflight.json`、`production-deploy.json`、`production-verify.json`、`public-and-gates-before.json`、`public-and-gates-after.json`、`public-comparison.json`。完整环境及容器检查仅留服务器。未提交或推送 Git，未执行生产压力测试、真实模型调用、真实用户面试创建或物理设备验收。短时健康检查不能证明长期 P95；后续结合真实流量的 P95、错误率和面试响应观察实际收益。用户可从[国际服登录](https://offersteady.com/login)测试普通面试、连续提问/回答、资料与设备状态；无需安装新的助手版本。
