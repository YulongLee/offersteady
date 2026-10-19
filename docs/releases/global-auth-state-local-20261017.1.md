# 国际服鉴权与状态读取优化：本地验收 2026-10-17

用户已授权同步本轮优化、自测通过后部署国际服。需求、非目标和逐场景验收见 [OpenSpec](../../openspec/changes/sync-global-auth-state-reads/proposal.md)、[设计](../../openspec/changes/sync-global-auth-state-reads/design.md)及[验证矩阵](../../openspec/changes/sync-global-auth-state-reads/verification.md)。

## 实际 Global 基线与最小增量

候选基于实际运行 Backend 镜像 `sha256:b31a810a49f718e360f8ddbcbae0e7aa3d0184012b8993cd0e2f5f973bc7657a`、容器 `c2b7caa35c86c85c13c4f9baeebb1da30465562d4ad50126c56db3d141d5bd4e`。重新读取的 236 个 app/Prompt 文件与上次实际发布源完全一致，冻结在 `artifacts/global-auth-state-20261017/baseline/`。独立候选仅替换八文件中批准的节点与两项 import，其余 228 文件、253 个未批准方法和剩余 AST 保持一致；74 个 Prompt 及三个问题预取源全部不变。未把混合工作区整包覆盖到国际服。

- 每请求用一条权威查询读取登录会话和账户是否可用，避免重复连接和读取完整用户资料；没有可跨请求缓存的“鉴权通过”结果。
- 同一登录会话的 `last_used_at_ms` 每 60 秒最多更新一次；条件更新只写使用时间，不覆盖退出、撤销、刷新、到期或改密后的安全状态。到期处理同样有条件保护，内存实现共用锁。
- 空闲状态读取仅取原五字段投影；列表内对重复资料 ID（包括不存在的资料）只读取一次，请求结束即丢弃 memo。
- 八个本来执行同步工作的 GET 路由交由既有同步执行机制处理，保留函数签名、装饰器、响应和错误语义。Global `/web/state` 的计费兼容、语言和正文均逐字保留。

Global 邮件/密码登录、默认及会话语言、Creem、独立会员和模拟面试原权益保留：七天购买准入、UTC 每日三场、无国服积分与 60 分钟截止；线上模拟开关原为 false，继续保留 false。助手仍为三平台 1.3.5，模型、Prompt、预取、heartbeat/ACK、Web/Admin、worker、数据库/Redis和国服均不在发布范围。不引入依赖、迁移、数据清理或真实模型调用。

## 本地验证边界

本地使用专用合成 PostgreSQL/Redis，网络限于本机测试端口及固定虚拟供应商。候选测试使用 `PYTHONPATH` 指向冻结 Global 源而非共享 CN 工作区；完整命令、退出码、测试数和日志见 `artifacts/global-auth-state-20261017/verification/` 的各组 JSON/XML。

合格候选 **368 项测试通过，另 16 个 subtests 通过，0 skipped**：auth/state 112、语言/会员/Creem 70、控制/预取 109、Global 实际 PostgreSQL 密码/语言 4、存储及 Global 超 60 分钟原行为 44、Global heartbeat/ACK/清理兼容 22（另 16 subtests）、其余相关合同 7。报告为 `artifacts/global-auth-state-20261017/candidate-verification.json`，SHA-256 `dd6e3101d72a9ecf0b9a5536cff1c683d9acaec896edae436a65ba2c8e4299b3`，与最终八文件 SHA 及七组成功记录绑定。

另有 800 次实际 Global 基线/候选合成鉴权调用，串行与八并发、窗口内与到期需 touch 各 100 次，零失败。窗口内 100 请求从 400 连接/300 SELECT/100 写行降为 100 连接/100 SELECT/0 写行；需 touch 时串行为 101 连接/1 次写行，八并发为 108 连接/8 次条件 UPDATE 但仅 1 行真正更新。撤销等安全字段全部保持，JWT 与权威状态仍逐请求核验。该 benchmark 不计入 pytest 数量，也不是生产压力测试；本机耗时不推算线上 P95。

共享测试含部分国服新接口及旧 Global 依赖差异。缺失的 CN 60 分钟接口、旧 publisher 立即移除约定及 cleanup helper 均在原 Global 基线复现；按实际 Global 合同单独验证，未给产品添加 CN 行为来满足测试。测试专用副本保留原断言 AST。初次测试 setup/返回值误认保留记录并修正后重跑；不能把这些结果表述为全仓测试全绿。

发布控制器、五道 Global 门禁及实际候选探针的保护检查合计 **273 项通过**（135 controller、128 gate、10 probe）。探针覆盖准确源、配置、路由、区域权益和禁止外部 IO，包含篡改拒绝用例；初次 Global 构造探针缺少 password hasher 的问题仅修复合成探针 setup。实际镜像探针和生产结果另见[发布记录](global-auth-state-20261017.1.md)。

本地合成结果用于说明减少重复数据库工作，不能作为真实用户流量的 P95 降幅承诺。未做真实模型、音频供应商、物理 Windows/macOS 收音或真实用户面试验收。
