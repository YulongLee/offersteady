## Context

用户授权“国际服同步这轮优化，自测后部署”。本轮迁移 CN 鉴权安全合同（历史国服参考：`../lighten-cn-auth-and-state-reads/specs/authoritative-efficient-authentication/spec.md`）和状态读取合同（历史国服参考：`../lighten-cn-auth-and-state-reads/specs/fresh-lightweight-state-reads/spec.md`），不是整包复制 CN 镜像。Global 具有独立邮箱/密码、语言、Creem 与模拟会员权益；[上一轮预取发布](../../../docs/releases/global-question-prefetch-20261016.1.md)记录实际镜像 `b31a810a…`、容器 `c2b7caa3…`，仅作为重核线索。发布前实际镜像、可写层、配置与完整路由尚待权威读取，不能预设已一致。

已有 [Global 密码生命周期](../add-global-password-authentication/specs/global-password-authentication/spec.md)、[网页状态协调](../sync-global-mock-and-companion-1-3-5/specs/global-web-state-refresh/spec.md)、问题预取、轻量 heartbeat、ACK 及 `openspec/specs/` 的会话恢复/资料合同都要保留。CN 本轮的连接与合成延迟数字不作为 Global 实测结果。

## Goals / Non-Goals

**Goals:**

- 每个有效请求仍校验权威会话与用户可用性，同时合并 PostgreSQL 读取、限频元数据写入。
- idle 只读取必要生命周期字段，会话列表仅在本次调用复用资料，八个同步状态 GET 避免阻塞事件循环。
- Global 账号、语言、商业和现有性能功能保持；合成自测、镜像保护和门禁通过后只上线 Global Backend。
- 发布和回退绑定实际运行组件，以可审阅脱敏证据区分合成测试、生产检查和未测量体验。

**Non-Goals:**

- 不更新 CN、Web/Admin/worker/数据库/Redis、Windows/macOS 助手或下载清单。
- 不改模型/Prompt、语言选项/默认值、Creem、会员/收费、模拟功能开关、客户端上报或指标口径。
- 不加正鉴权/跨请求资料缓存、连接池、新依赖、迁移或 schema 变化；不把旧 refresh/logout writer 全部原子化。
- 不创建真实用户/收费面试、调用真实供应商、生产压测、导出原始日志/凭据或提交/推送 Git。

## Decisions

### 1. 从实际 Global 源逐节点构造八文件增量

先冻结实际 Backend Image/容器与裸镜像/可写层源码，完整 app/Prompt 哈希、有效模型/配置、原 Compose 全顺序/项目目录/Env/HostConfig/挂载/网络及所有非目标组件。运行载荷只涉及：

- `apps/backend/app/ports/authentication.py`
- `apps/backend/app/services/authentication_service.py`
- `apps/backend/app/services/authentication_repository.py`
- `apps/backend/app/services/postgres_authentication_repository.py`
- `apps/backend/app/services/session_service.py`
- `apps/backend/app/modules/session.py`
- `apps/backend/app/modules/web.py`
- `apps/backend/app/modules/realtime_speech.py`

将已验收 CN 优化的批准节点迁入 Global 对应节点，而非整文件覆盖。构造函数仅增加必要共享锁，保留 Global 现有 email challenge 等字段；认证服务的密码/邮件/语言方法及网页 state 区域正文不迁移。其余所有文件、八文件中的未批准方法/AST、已发布预取三文件、heartbeat/ACK、Prompt 和助手清单逐一保护。若基线已包含某项优化则验证其等价性，不重复或强行覆盖。

替代方案是从工作区或 CN 最新镜像完整重建，容易覆盖 Global 专有行为；不能采用。存在漂移时先保护新实际差异并重新验证同范围最小候选，不直接应用历史候选。

### 2. 沿用逐请求权威读取和限频安全元数据更新

`get_access_token_state` 用一个 PostgreSQL 连接/SELECT 取得会话及用户存在/active restriction 可用性；不为未消费的完整 profile、密码、bindings 再开连接，不增加新的 bindings.status 准入条件。内存实现保留 `get_user` 扩展语义。Global 的错误结构、缺失/到期优先级、最小 schema 原兼容回退和凭据生命周期保持，不能把数据库读取失败当成成功授权。

`last_used_at_ms` 仅在相隔至少 60 秒后的合法请求更新；CAS 比较会话 owner、active/revoked、有效期、refresh 指纹、issued 等安全快照，只 UPDATE 活动元数据，无 UPSERT。常态一个连接/一个 SELECT，到窗口时允许额外条件更新连接；并发请求可有多次尝试但同窗口至多一次实际行写。会话过期持久化使用同类 CAS，不覆盖已提交刷新/撤销/删除；内存保存与 CAS 共享锁。签名有效但 `typ != access` 显式拒绝；有效 access 的 key、算法、issuer、claims 不变。

即时安全以本次权威读取时点为准；不引入跨请求授权宽限，也不宣称消除所有在途请求竞争。正鉴权 TTL 缓存、仅 JWT 校验或异步活动写队列会扩大撤销/资源边界，本轮不采用。

### 3. 状态效率只改变取数方式与执行位置

idle 复用现有五字段 heartbeat 投影，保留归属/404/403、原边界及调用方 reconcile 的结束/计费/资源释放，不新增 idle 副作用。`list_sessions` 在本次调用内按 document ID 缓存读取结果（含 None），保留 mock 直接返回的版本归属路径；后续请求重新读取 ready、删除、版本和索引状态，不引入跨 owner/请求缓存。

session list/get/review/idle、web state、realtime runtime/last-used/list-devices 共八个纯同步 GET 从 `async def` 改 `def`，由现有 FastAPI/AnyIO 线程池执行。签名、装饰器和正文逐字保持 Global 实际版本，尤其 Global `usage_billing_service`、语言与账户字段。已有 realtime control 独立执行器、heartbeat/ACK 和预取资源边界不改。使用真实 ASGI sentinel 验证慢同步 IO 期间 loop 可推进、错误及取消后能恢复；不声称任意底层同步 IO 可被取消或执行池不会饱和。

### 4. 区域行为用源保护与合成执行双重验证

Global 保留邮箱验证码/密码/注册/刷新/改密/重置/退出、默认和面试语言、Creem 和独立 Admin。模拟权益仍为七天及以上购买套餐准入、UTC 每日三场，无 CN 积分钱包和 60 分钟截止。历史 `mock_interview_enabled=false` 在本轮实际读取后仍须保持 false；隔离测试可启用验证，不在生产开放。全部 Prompt/模型/语言规则和助手 1.3.5 发行物保持实际基线。

候选在独立进程和本地 loopback 合成数据库/schema 运行安全/SQL 计数/并发 CAS、密码/邮件/语言、状态 sentinel、Creem/权益及预取/heartbeat/ACK 回归。测试依赖按实际 Global module 绑定，不伪造不存在的 CN provider；任何旧失败须在原实际源复现并记录，不能扩大实现以追全仓绿。没有 AI 行为变化，现有 eval 可回归，Prompt 全哈希保护；不新增 AI 行为或编造新效果结论。

### 5. 完整运行路由保护与独立基线恢复门禁

沿用 CN 最新控制器已验证思想，但不得复制 CN 195 个运行路径或 Global 旧 151 个 shell 路径作为当前完整路由期望。离线 shell 只验证选定业务模块；另从实际运行应用读取完整 HTTP 路径/方法和 OpenAPI schema SHA，覆盖 Admin/公开入口并冻结前后比较。候选 probe 在 network none、只读、禁止 DB/网络/文件写入/worker/lifecycle 下验证源/Prompt/节点与合成鉴权，不把离线 shell 当作真实完整 main。

冻结实际原镜像和完整有效配置；控制器合成测试覆盖源/配置/路由/门禁/身份漂移、仅切 Backend、失败和恢复。恢复活动门禁不得依赖故障候选容器能正常 import、健康或其已漂移环境；使用冻结原镜像、原环境与网络的独立只读门禁上下文，并核对该私有上下文本身未漂移。

### 6. 无保护活动时只切 Global Backend 并实证验收

切换前重复权威门禁和身份核对：普通/笔试/模拟、近期准备、网页/桌面租约、音轨/发布者、回答/截图及资料工作。受保护活动非零、过期采样、未知状态或读取失败时不重启/切换，不清数据制造空闲。用户已授权上线；遇活动可等待真实空闲，不另行询问同一授权，不擅自承诺未来自动调度。

仅版本私有 overlay 指向固定候选镜像 ID，保持 Compose 顺序/项目目录、环境/HostConfig/挂载/网络、共享标签和源码指针。验证实际源/Prompt/完整路由/schema、模型/配置、所有非目标组件、匿名 Global health/login/会员目录/mock capabilities/Web build 标识和短时脱敏错误。非动态公开数据前后摘要保持，mock false 仍须一致。

失败恢复先确认当前容器属于本次、无后续发布、配置/镜像归属明确并执行安全活动检查，只恢复本次原 Global Backend；无法判断即停止覆盖并报告。成功也另行 verify 并说明真实 P95、供应商和实体设备尚未验收。替代的无门禁重启或按共享标签回退会影响用户/覆盖后来发布，不采用。

## Risks / Trade-offs

- [混合 CN 源覆盖 Global 账号或权益] → 实际镜像逐节点增量、所有非批准 AST 与语言/商业合成回归。
- [touch/expiry 覆盖安全变化] → 条件 UPDATE、共享内存锁、隔离 PostgreSQL 受控交错；不承诺所有历史 writer 已原子化。
- [资料复用扩大缓存边界] → 仅局部 document ID memo，含 None、mock 版本、下请求和跨 owner 场景。
- [线程池仍排队] → sentinel 与负载计数说明执行边界，结果不等于生产 P95 保证。
- [shell 探针漏完整 Admin/公开路由] → 独立冻结实际完整 HTTP/schema；不复用 CN 或旧 Global 数量。
- [恢复依赖坏候选或覆盖后续发布] → 冻结基线独立只读门禁，严格发布/配置归属与新活动检查。
- [私有环境或用户数据泄露] → 私有备份留服务器，仅导出哈希/计数/固定错误摘要，测试纯合成。

## Migration Plan

没有 schema/依赖迁移。权威重核 Global 实际基线 → 最小八文件候选/全源与完整路由保护 → 隔离合成测试/独立审查 → 固定镜像与离线 probe/发布回归 → 重复活动/身份门禁 → 仅 Global Backend 切换 → 独立 verify 与短时观察。失败按归属安全恢复，保留旧真实镜像。CN 与所有非目标组件不动，Git 不在范围内。

## Open Questions

没有阻塞产品决策，授权足够。实际 Global 当前 image/container、配置、全源和完整路由尚待发布执行者读取；这些是必须验证的前置条件，不能当未标注假设。真实负载下收益仍未知；若实际基线无法满足本文保护合同，停止切换并报告。
