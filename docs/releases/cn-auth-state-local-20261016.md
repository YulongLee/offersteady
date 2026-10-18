# 国服鉴权与状态读取优化：本地验收

本轮根据 [API P95 诊断](../diagnostics/cn-api-p95-20261016.md)完成后端冗余读写优化，对应 [OpenSpec 提案](../../openspec/changes/lighten-cn-auth-and-state-reads/proposal.md)、[设计](../../openspec/changes/lighten-cn-auth-and-state-reads/design.md)和[任务](../../openspec/changes/lighten-cn-auth-and-state-reads/tasks.md)。用户只授权本地开发与自测，**本记录不表示已上线**。

## 行为和影响

- 每次有效鉴权仍读取当前会话、用户存在及封禁状态。PostgreSQL 将原来的会话、完整用户、身份绑定读取合并为一次权威查询；不增加跨请求鉴权缓存，不改变退出、封禁和原有令牌生命周期。
- 登录会话的最近使用时间改为相隔 60 秒后、下次合法请求到达时更新。它是使用时间元数据，不控制授权；会话列表中该时间的精度相应降低。更新只改这一字段，不能插入被删除的会话、恢复撤销状态或覆盖刷新后的凭据/有效期。到期持久化同样使用条件更新。
- idle 状态读取复用已有五字段生命周期投影，避免读取完整会话和绑定资料；原归属、超时结束、计费和资源释放路径保留。
- 同一次会话列表读取对相同资料只查询一次，包括不存在的资料；下一次请求重新读取。模拟面试原有资料版本归属路径保持。
- 会话列表、详情、复盘、idle、网页聚合状态及三项设备/runtime GET 入口交给现有 FastAPI/AnyIO 线程池执行同步读取。八个入口除 `async def` 改为 `def` 外，正文、签名和装饰器保持不变。
- JWT 解码补充已有 access 类型合同的拒绝校验：签名有效但类型非 access 的令牌返回 401。没有改变合法令牌的算法、issuer、密钥或有效期。

没有新增依赖、迁移、模型/Prompt 或客户端改动。国服会员每日一场免费、其余 100 积分、开始后 60 分钟结束，国际服独立权益、Admin、Windows/macOS 助手及现有功能开关均不在本轮变更范围。

## 实际运行基线与候选保护

只读核对的国服 Backend 镜像为 `sha256:cc040a55f261a37226272c31937744e6ca4bd7a8c25e0810e360d218d41acfc0`，容器为 `7e3ea04495bcaec9d8c072b892dcd86a87735af4ada2f002aaef92eae1039d25`，采集时 healthy、重启计数 0。168 个 app/Prompt 文件与本地冻结基线逐一核对一致。

候选直接以该基线逐节点迁移八个目标文件：四个鉴权文件、SessionService 和三个状态路由模块。工作区包含区域差异，不能整体覆盖实际国服源码；尤其内存仓库构造函数仅插入锁初始化，网页 state 保留实际国服正文。候选另外 160 个文件、210 个未批准方法逐字节不变，其余非批准 AST 也与基线相同。已有 Chat、RealtimeSpeechService、问题预取调度器保持原文件 SHA。

无网络/数据库/文件写入/worker 启动的路由 shell 验证通过：140 个 HTTP 路径、两条模拟面试 WebSocket、19 个路由模块和全部 20 个 Prompt 保留；完整 OpenAPI SHA 为 `87d07432b35c17df7c71411c73725e7d11e22b3b2f83032b4a71393f3cb5def1`，前后完全一致。

本地证据位于 `artifacts/cn-auth-state-20261016/` 的 `baseline-binding.json`、`candidate-proof.json` 和 `routing-proof.json`。`baseline/`、`candidate/` 另附共享 migration/eval/格式资产用于测试，它们不属于八文件运行源码补丁。本轮没有构建或切换生产镜像。

## 合成对照

鉴权使用同一合成账号、会话和绑定、真实签名 JWT、独立子进程与一次预热后重置的本机 PostgreSQL schema。四组条件各比较基线/候选 100 次调用，共 800 次，失败 0；耗时从 worker 开始执行鉴权计量，不含执行器排队时间。

| 常态鉴权（100 次） | 实际基线 | 候选 |
| --- | ---: | ---: |
| 数据库连接 | 400 | 100 |
| SELECT | 300 | 100 |
| 整行 UPSERT / 实际写行 | 100 / 100 | 0 / 0 |
| 并发 1：P50 / P95 / P99 | 21.075 / 25.862 / 27.638 ms | 4.828 / 6.646 / 7.611 ms |
| 并发 8：P50 / P95 / P99 | 53.980 / 69.117 / 83.479 ms | 10.402 / 21.317 / 23.074 ms |

60 秒更新窗口刚到时，候选单并发 100 次调用为 101 个连接、一次实际更新；并发 8 为 108 个连接、八次条件更新尝试、仍仅一行实际更新。这些是请求同时读到旧使用时间后的条件竞争，PostgreSQL 路径没有增加应用级串行锁或全局连接池；内存仓库使用共享 RLock 保护活动更新与会话保存。

状态对照使用十个会话、三份共享合成资料，资料读取替身固定等待 1 ms。每种路径、每个并发条件、每个版本均为 64 次调用，共 512 次，失败 0；此处为服务调用，不是 HTTP 或真实数据库延迟。

| 状态路径（64 次） | 实际基线 | 候选 |
| --- | ---: | ---: |
| 会话列表资料读取 | 1,920 | 192 |
| idle 完整会话 / 资料读取 | 64 / 192 | 0 / 0 |
| idle 轻量投影读取 | 0 | 64 |
| 列表并发 1：P50 / P95 / P99 | 46.778 / 48.624 / 55.069 ms | 4.772 / 5.184 / 5.209 ms |
| 列表并发 8：P50 / P95 / P99 | 46.889 / 55.660 / 58.203 ms | 4.764 / 5.388 / 5.458 ms |
| idle 并发 1：P50 / P95 / P99 | 4.752 / 4.875 / 5.033 ms | 0.001 / 0.002 / 0.011 ms |
| idle 并发 8：P50 / P95 / P99 | 4.672 / 5.025 / 5.108 ms | 0.001 / 0.005 / 0.007 ms |

以上证明减少了指定路径的工作量，不是线上整体 P95 降幅承诺。尚未测量真实流量的请求排队、网络、供应商响应、默认线程池饱和及最终端到端体验。完整数据见本地 `benchmark-auth.json`、`benchmark-state-baseline.json`、`benchmark-state-candidate.json`；可复现脚本在同目录 `verification/benchmark_auth.py`、`benchmark_state.py`。

## 测试与已知边界

工作区新增鉴权内存 34 项、隔离 PostgreSQL 19 项、状态 40 项，共 93 项专项通过。连同 Global 密码/邮箱生命周期、核心认证、状态合同、心跳/清理等相关回归，工作区合计 185 项通过。独立审查另跑了其中 74 项，并核对条件 SQL、锁与八入口 AST，没有发现本轮引入的需修复问题。

PostgreSQL 专项包含逐请求权威读取计数、60 秒边界、32 次并发仅一次实际 touch、在旧请求读取后已提交撤销/删除/到期/刷新/改密的受控竞争及到期 CAS。状态专项包含零资料 idle、每请求资料去重及下次变化、归属/404/403、真实 ASGI 阻塞读取期间的事件循环推进、业务错误和取消后 worker 释放及后续恢复。它们不代表已原子化所有旧 refresh/logout 整行 writer，也不保证取消可以中断任意底层同步 IO。

既有 `test_wechat_compatible_login_is_disabled_in_production` 的错误码断言仍失败：实际使用通用 `domain_request_error`，测试期待 `wechat-production-disabled`；阻断和 404 正常。使用改前 AuthenticationService 在独立进程复现同一失败，未为本轮优化改变既有错误封装。

实际国服候选中的鉴权专项为 52 项通过、一项 Global 专有生命周期跳过；相应 Global register/reset 流程已在工作区实现中通过，国服实际源没有这些 Global 方法。本轮没有向候选注入其它区域实现。

实际国服候选其余最终合格集合为 **381 项通过，另 16 个 unittest subtest 通过**，该集合无失败、错误或跳过。合并上述鉴权后为 433 项通过、另 16 个 subtest、一项 Global 专有跳过，不能重复累加前面的工作区或独立复核结果。

| 国服候选集合 | 结果 | 证据 |
| --- | --- | --- |
| 新增鉴权安全与实际 PostgreSQL | 52 通过，1 Global 专有跳过 | `verification/auth-candidate.xml` |
| 状态、轻心跳、ACK、控制、预取、清理及模拟隔离 | 294 通过，另 16 个 subtest；13 项已知差异排除 | `verification/cn-candidate-core-qualified.xml` |
| PostgreSQL/Redis、模拟 API、积分/免费次数及 deadline | 78 通过 | `verification/cn-candidate-storage.xml` |
| 会话、资料、网页、复盘、设备/runtime 合同 | 9 通过 | `verification/cn-candidate-state-contracts-monotonic.xml` |

本记录不宣称全仓测试全绿。较宽共享测试的 13 项差异已在未改动的实际国服基线逐项复现：一项要求工作区新增的 ACK 诊断 helper，11 项要求实际国服尚未包含的 mock close/log 行为，一项是 Global 独有 TTS 分支。没有为使这些测试通过而迁移无关产品代码；原失败报告与最终筛选命令均保留在本地 `verification/baseline-known-differences.json`、`candidate-initial-results.json` 和 `candidate-regressions.json`。

会话最近五条的旧测试还假定连续创建不会落在同一毫秒。固定同毫秒的合成时钟下，原基线与候选均在同一排序断言失败；最终九项合同测试仅对此旧测试提供单调合成时钟，原排序代码和断言均未改变，两个版本均通过。新增状态测试初次依赖了工作区 Global 专有 billing provider，已将 setup 改成只覆盖实际存在的依赖；40 项在工作区与国服候选各自通过，59 个 assert 的 AST 全部保留。适配证据在 `verification/test-portability-adaptation.json`、`candidate-state-portable.json` 和 `fixed-clock-tie-proof.json`。

本机 PostgreSQL/Redis 仅使用专用合成数据库/schema；候选回归网络只允许 `127.0.0.1:55445` 和 `127.0.0.1:56385`。测试没有复制真实用户数据、调用真实模型或音频服务。准确命令与 JUnit 保存在本地验证目录。

## 后续上线条件

本轮只在开始时只读核对国服实际基线；没有部署、重启、修改生产配置/数据库、生产压测、创建真实面试或提交/推送 Git，国际服及其它线上组件没有变更。

用户晚上另行要求上线后，应重新核对各目标组件当时实际镜像和源，复用已验收最小候选并校验是否漂移，再按既有活动门禁发布。当前本地源码验收不替代当晚的实际运行状态核对与生产验收。
