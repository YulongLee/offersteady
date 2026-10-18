## Context

[诊断记录](../../../docs/diagnostics/cn-api-p95-20261016.md)中的峰值窗口有 1,255 次 performance-ack，约占全部请求 45%，贡献约 58% 的秒级慢请求。运行代码的每次有效 Bearer 鉴权分别读取 auth session、用户和身份绑定，并写 last-used；这些成本发生在 ACK 会话缓存之前。部分异步状态路由还直接执行同步服务读取。现有数据没有逐阶段耗时，优化目标是消除已确认的冗余工作和阻塞风险，而非预设唯一根因或承诺线上 P95 数字。

既有[权威鉴权合同](../establish-authentication-service/specs/authentication-service/spec.md)、[轻量心跳](../lighten-cn-web-heartbeat/specs/lightweight-web-heartbeat/spec.md)、[ACK 兼容](../fix-cn-performance-ack-compatibility/specs/runtime-performance-ack-compatibility/spec.md)和[预取边界](../coalesce-cn-question-prefetch/proposal.md)必须保留。长期入口/资料行为仍以 `openspec/specs/` 的既有规范为准。共享 Backend 同时服务 CN 与 Global，商业规则和密码会话生命周期不能串用。

## Goals / Non-Goals

**Goals:**

- 每次受保护请求维持权威安全检查，同时减少独立连接和往返，降低高频重复元数据写入。
- 只需生命周期的读取避免完整资料/配置/对话反序列化；需要资料时仅在同一次请求内复用读取结果。
- 选定异步状态路由执行同步仓库/服务读取期间，事件循环仍可推进不依赖该 IO 的工作。
- 用可复现合成测试验证安全、资源计数、契约和区域兼容，准备可审阅的本地实际镜像最小候选。

**Non-Goals:**

- 不部署、重启、压测生产服务，不创建真实面试，不执行 Git 提交或发布；上线需用户后续授权。
- 不增加跨请求正鉴权缓存或跨请求资料缓存，不引入连接池、新依赖或数据库迁移。
- 不改客户端上报频率、公共路由/字段/错误、计费/会员/模型/Prompt/功能开关、指标分类或 P95 算法。
- 不改变已有 ACK 正缓存、心跳租约、问题预取调度和清理策略，不进行无关整文件覆盖。

## Decisions

### 1. 用请求内鉴权快照合并权威读取

令牌签名、类型、到期等纯校验沿用现有边界。新增仓库 `get_access_token_state(session_id, user_id)` 返回会话与用户可用性布尔值；PostgreSQL 在一个连接、一个 SELECT 中读取会话，并通过 EXISTS 取得用户存在与活跃限制判断。原鉴权只使用 `_require_user` 的存在/限制判定，完整 UserRecord、密码和 identity bindings 不参与其后授权，故不再为鉴权加载它们；不得借机增加 bindings.status 等新准入条件。绑定变更按原流程引发会话撤销时，继续通过权威会话状态生效。

源代码核对同时发现 `JWTAccessTokenCodec.decode_access_token` 原来把解码后的 `typ` 无条件构造成 `access`，未落实既定无效类型拒绝场景。本轮仅在同一解码函数增加显式拒绝合法签名但 `typ != access` 的最小校验，并补充回归；签名算法、密钥、issuer 和有效 access claims 合同不变，不扩大令牌体系或密码策略。

快照仅供本次请求使用，不写入正鉴权缓存。不存在、撤销、过期、用户不可用/封禁结果与原路径一致，错误路径不得 touch。常态为一个连接、一个 SELECT；达到 touch 时间窗口才可能开启第二个连接作元数据条件更新，不承诺所有路径只使用一个连接。

选择这一方式是为了减少重复 IO，同时保持后续请求即刻看到已提交的安全变化。替代方案包括短时正缓存、仅校验 JWT、先接入连接池；前两项引入撤销滞后，连接池增加资源生命周期和依赖范围，均不在本轮采用。精确 SQL 形状须根据实现审查确定，验收以等价安全结果和连接/查询计数为准。

### 2. last-used 使用限频、条件式元数据更新

`last_used_at` 是使用元数据，不是授权依据。以 60 秒为更新窗口，使用数据库条件更新而非先读后覆盖整会话；只更新 last-used 等明确批准的活动元数据，不修改会话状态、有效期、refresh token、凭据或撤销时间。更新条件须防止并发撤销、过期、令牌轮换及登录凭据变化后写入旧快照，目标不存在时不得 UPSERT。

内存仓库维持相同外部语义，并通过可控竞争测试核对。touch 使用读取时安全字段的 CAS 条件，并发合法请求在同一窗口最多产生一次实际行更新；未到间隔不写行，不延长令牌/会话有效期。会话过期状态持久化也使用 CAS，防止旧读取覆盖并发刷新/撤销的新状态。元数据更新失败遵循既有服务错误处理，不得吞掉安全读取失败或把失败当成授权成功。安全变化的即时性以每次请求的权威读取时点为准，不增加跨请求宽限，不声称消除所有在途请求竞争窗口。

替代的异步排队活动写入会增加停机丢失与资源队列，不采用；整对象 save 有覆盖已撤销状态的风险，不能用于 touch。

### 3. 生命周期投影与资料读取分别保持合同

对 idle/status 等只需生命周期的路径读取必要字段，显式保留 owner、删除标记、生命周期、超时所需时间及原响应依赖。不能以投影绕过归属校验、idle-timeout 收尾/计费/资源释放或 lease 更新。软删除和不存在仍为原错误，不缓存 ended 或 owner。

`SessionService.idle_status` 复用已有五字段 `heartbeat_idle_status` 投影，保留原结束结算与错误；这是对 idle 状态读取的新优化，不改变旧心跳能力。

完整会话和网页聚合状态仍按原规则验证绑定资料。`list_sessions` 在本次调用内按 document ID 记忆文档读取结果（包括不存在的 None），供各会话 `_refresh_bound_document_activity` 复用；缓存只存在于局部变量，单个不同 document ID 至多调用一次文档读取，owner 仍由原会话列表和读取边界限定。mock 会话继续直接返回、不刷新其选定版本。下一次请求必须重新取得资料权威状态，删除/撤销/版本/ready 状态立即反映。不能跨 owner 复用请求上下文、创建新的允许清单或静默替换已选资料。

替代方案是给状态/资料添加 TTL 缓存，容易扩大资料授权和数据新鲜度边界，本轮不采用。

### 4. 将同步读取整体分流，保留原资源策略

八个纯同步读取的状态 GET 入口（session list/get/review/idle、web state、realtime runtime/last-used/list-devices）从 `async def` 改为 `def`，由现有 FastAPI/AnyIO 线程池执行原服务正文，保持原 Pydantic/JSON 契约。web state 正文不改区域差异；不在线程中复用 async-only 对象或事务，不增加新执行器或无限后台任务。已有 heartbeat/control 独立执行器继续使用原路径，避免把它们静默合并进默认池；不会用线程分流取代权威校验。

验收使用可控阻塞替身与事件循环 sentinel，确保 IO 未完成时 sentinel 可推进；同时测试异常/取消后的正常响应和资源释放。只改排队位置并不保证无等待，因此补充合成并发比较和失败计数；不宣称这已量化真实线上收益。

### 5. 实际运行镜像保护与本地交付

基线以诊断确认的 CN Backend Image `sha256:cc040a55f261a37226272c31937744e6ca4bd7a8c25e0810e360d218d41acfc0` 为线索，但候选制作前须核对实际镜像/源包证据一致，不将工作区或 `current`、版本字符串作为线上事实。仅在本地对保存的实际镜像源码施加经审阅最小节点补丁，比较全源码/路由/方法/模块/Prompt 及未批准节点，确认已发布预取、轻量心跳、ACK 和 Global 相关能力未回退。

本地 `artifacts/cn-auth-state-20261016/baseline-binding.json` 已绑定上述实际镜像与容器，168 个 app/Prompt 文件与保存源逐一哈希一致；`working-before/` 冻结了八个目标源码且与当时 HEAD 一致。此为本地已有证据，不代表最终候选已通过，也不代表本轮已操作线上。

本轮不执行任何生产切换；基线无法取得时如实记录候选保护未验证，不能把工作区单测冒充镜像候选通过。未来上线须重新核对实际状态、空闲门禁与回滚基线，不能直接从整个组合工作区重建国服。

## Risks / Trade-offs

- [合并读取误吞某个缺失/限制状态] → 对照旧服务结果、CN/Global 合成用户矩阵，检查每个条件均保留。
- [touch 覆盖并发安全变更或复活会话] → 使用受限字段条件 UPDATE，无 UPSERT，加入真实隔离 PostgreSQL 竞争与刷新/改密回归。
- [稀疏投影遗漏 idle 清理/租约字段] → 对照 preparing/live/warning/expired/ended/删除/跨用户完整响应和副作用。
- [请求内资料复用变成跨请求或跨 owner 缓存] → 明确上下文作用域，连续请求中修改资料及跨账号场景回归。
- [线程执行池排队仍在或共享对象不安全] → sentinel、并发/异常测试并保留已有独立控制池；不增加未界定的新队列。
- [合成数字无法代表线上流量] → 输出负载、样本数、计数和失败数，明确没有真实 P95 降幅保证。
- [工作区混合多次开发误覆盖线上补丁] → 候选从实际镜像构建，审查全源差异和非批准节点；本轮不发布。

## Migration Plan

无需迁移、新依赖或配置变化。本地完成安全回归、隔离 PostgreSQL、异步路由/现有功能测试、合成资源计数和最小镜像候选保护后交付结果；不推送代码或切换服务。晚上用户要求上线时，再按当时实际镜像与空闲门禁单独组织可回滚发布。

## Open Questions

没有阻塞产品决策。具体单次 SQL/线程池/事件循环在今天峰值中的耗时比例尚未测量；这是收益测量的限制，不是放宽安全合同或增加本轮范围的理由。若实现无法维持本文安全/新鲜度合同则停止该项优化并报告。

## 2026-10-17 Production Release Addendum

### Authorization and historical scope

本文前述“不部署/只本地”决定适用于已交付的 2026-10-16 本地开发阶段，原验收记录及 SHA 不改写为生产验收。2026-10-17 用户已明确授权将这一轮优化部署到国服；本节及新增 `cn-auth-state-protected-release` 能力约束本次上线，不扩大业务功能，也不要求重复确认。

### Exact runtime payload

复用 [本地验收](../../../docs/releases/cn-auth-state-local-20261016.md)及冻结候选，运行载荷仅含以下八个文件的批准节点：

- `apps/backend/app/ports/authentication.py`
- `apps/backend/app/services/authentication_service.py`
- `apps/backend/app/services/authentication_repository.py`
- `apps/backend/app/services/postgres_authentication_repository.py`
- `apps/backend/app/services/session_service.py`
- `apps/backend/app/modules/session.py`
- `apps/backend/app/modules/web.py`
- `apps/backend/app/modules/realtime_speech.py`

八文件之外的 app/Prompt 清单及八文件中的未批准节点均以实际组件为准保持；八个状态入口只允许既定同步声明变化，国服 web state 正文不能被工作区 Global 差异覆盖。已发布预取三文件、轻心跳、ACK、收费/60 分钟 deadline、助手下载清单及模型/功能开关保护均纳入 probe。禁止携带测试迁移/eval 资产当作额外运行补丁；本次不引入新依赖、数据库迁移或 schema 变化。

### Rebind before mutation and fail closed on drift

发布执行者先重新读取当前 CN Backend 的真实 Image ID、容器及可写层源码、所有 app/Prompt 哈希、完整路由/OpenAPI、有效模型/配置和 Compose 顺序/项目目录/环境/HostConfig/挂载，记录所有非目标组件身份。`cc040a55…` 和旧容器仅是已验收候选的历史绑定，不能凭版本字符串、共享标签或发布目录推断仍在运行。

只有实际基线、冻结候选及非批准内容全部一致时才能直接复用。发现镜像/源/配置漂移，拒绝直接切换旧候选；先保留当时实际差异并重新制作/验证最小增量，不能覆盖它们或悄悄修改发布边界。任何待执行变更仍须保持上述八文件批准节点范围。切换前再次核对部署身份和候选完整性，防止准备期间出现其它发布。

### Isolated candidate and protected-work gates

冻结候选与不可变原镜像回退基线后，先完成无网络/只读且拒绝数据库、供应商、子进程、线程启动和持久化写入的候选 probe；不启动完整应用生命周期、不创建真实用户/面试或调用真实模型。执行本次发布控制器的合成回归，覆盖镜像/配置漂移、活动/不确定门禁、只改目标容器、发布后失败和安全回退分支。

临近切换重复执行既有权威活动门禁：普通/笔试/模拟面试、近期准备、网页/桌面租约、音轨/发布者、回答/截图任务及资料后台工作。任何受保护活动非零、数据源失败、超时或结果不确定均不重启、不切换；不得结束面试、删除活动记录或放宽现有排除口径制造空闲。若沿用先前明确的陈旧失败任务例外，只允许相同条件且单列原因/计数，不把异常任务整体忽略。

### Backend-only cutover and owned rollback

在连续门禁和身份校验通过后，仅用版本私有 overlay 将 CN Backend 指向固定镜像 ID，保留有效 Compose 顺序/项目目录、环境、HostConfig、挂载以及网络/IP 策略；其他组件不重建、不更新共享镜像标签，不依靠修改源码指针切换。变更前保留原镜像与私有配置备份，普通记录只输出脱敏摘要，不导出凭据。

切换后检查容器 healthy/重启数、全源及 Prompt/路由/OpenAPI、有效模型/配置、非目标组件身份，检查匿名 `/healthz` 和 `/login` 及短时脱敏错误/5xx 摘要。不得把离线 probe 说成真实面试功能验收，也不得将短时健康误称真实负载 P95 已改善。

失败恢复仅由当前发布归属控制：确认没有后续部署、配置和镜像未被别的发布改变，并完成活动安全检查后，才恢复本次冻结原 Backend 镜像/配置，再核对恢复健康及保护项。若归属或活动无法确认，停止自动覆盖并报告实际状态，不回滚国际服或其他组件。

### Release evidence

生产记录另写实际发布时间、前后 Image/容器、有效部署配置摘要、门禁/候选/切换/验证/恢复的真实结果，以及未做的真实流量和物理客户端验收。本地 `final-verification.json`、候选合格集合和旧差异说明仍保留原来日期及 local-only 事实，不改写或覆盖。
