## Context

状态：用户于 2026-10-16 已明确授权国际服同步并上线。国服本轮优化及其合成测试已经通过并发布，国际服仍需独立读取实际运行镜像/source，而不能以共享 Git 封版、`current`、旧发布目录或健康版本字符串代替组件基线。上一轮国际服实际发布记录见 [Global 1.3.5](../../../docs/releases/global-mock-companion-1.3.5-20261015.md)；其中镜像仅供核对历史，当前值必须重新采集。

本轮范围沿用 [国服预取设计](../coalesce-cn-question-prefetch/design.md)，仅迁移相关优化节点到实际 Global Backend，保持国际服独立会员、UTC 额度、语言/模型与已关闭模拟面试开关。已有 Global heartbeat、ACK、P95 分类和上一轮模拟资源清理/诊断必须保留。

## Goals / Non-Goals

**Goals:** 减少连续稳定字幕的重复后台工作；保留首段及时准备、final 优先、有限状态和安全清理；资料/身份变化时拒绝旧缓存；用户点击不等待预取；用隔离合成数据及实际镜像候选证明行为，再进行受保护的国际服单 Backend 发布。

**Non-Goals:** 不变更 Global 商业权益、普通/模拟收费、语言选择、Prompt、模型/TTS、Creem、功能开关、音频协议、字幕事件、客户端 question ID/revision 合同、连接池、指标口径或环境变量；不发布 Web、助手、Admin、worker、数据库/Redis 或 CN；不将合成调用下降等同线上 P95 降幅；不调用真实用户内容或供应商作为测试。

## Decisions

1. 复制已验证的小型调度器，并仅将 Chat/Realtime 的获准节点适配到 Global 实际源：两个固定 worker、最多 256 个 key、350ms quiet、1500ms max wait、10s pending TTL，单键保留最新待办。leading 立即、final 优先，空闲第二 worker 可绕过同键旧 partial；总并发始终不超过二。继续共用 cold 队列会保留旧问题堆积；每字幕 Timer/Future 会使隐藏队列无界，因此保持专用有限调度。
2. Chat 缓存按 owner/session、规范空白后的完整问题和 retrieval-visible 当前资料指纹校验；最多 128 个问题、60s TTL，包含 bound document 版本、状态、索引、active、collection 等。partial/final 文本不同不以子串命中，优先正确引用。点击复用现有授权 session 快照，miss 保留原 quick fallback，detail 独立检索。
3. 维持纯内存 token 与 generation 撤销：锁外做外部调用，检索前后及提交/命中安全边界复核；清理、reset、shutdown 后旧 observer 不能重建状态或旧结果复活。同步 IO 自然结束，不强杀 SQL/HTTP，不取消无关 cold usage/持久化工作。
4. 候选从重新核验的实际镜像构建；完整枚举 app/Prompt 哈希、已有路由、受保护方法、有效模型/config、下载 manifest 与其它组件身份。Chat/Realtime 以方法/节点 allowlist 迁移，不整文件复制共享工作树。除三项目标外所有源码和 Prompt 必须逐字节不变；目标文件非批准 AST 节点也必须不变。镜像裸文件与运行容器差异必须解释并保护，发现未预期漂移停止切换。
5. 验证在仅本机专用合成数据库/Redis 与固定 provider 中执行，候选镜像探针拒绝外部网络、数据库、持久写入及应用生命周期。对比实际基线与候选的 admitted 检索/会话读取、leading/final、点击非等待和资料引用；国际服独立权益、英文及其它语言/Prompt/模型、heartbeat/ACK/普通/模拟隔离纳入保护。
6. 只通过私有、固定不可变镜像 ID overlay 替换 Global Backend，保留实际 Compose 文件顺序、project directory、环境、HostConfig/挂载与其它组件。切换前即时检查普通/笔试/模拟、页面/桌面租约、音轨、生成、截图与资料活动；任何受保护工作或检查不确定都不切换。相比整栈重建，该最小切换缩小了影响面，并使实际旧镜像可核验回退。

## Risks / Trade-offs

- 更严格完整问题匹配导致部分 partial 缓存 miss → 保留 leading/final 优先与原 quick fallback，测试即时和已有准备时间两种点击窗口及 detail 资料正确性。
- Global 代码与共享源码不一致 → 实际镜像基线、批准节点 diff、全源/Prompt/路由与独立收费回归；不使用 Git 版本作为区域运行承诺。
- 同步 IO 慢或清理竞态 → 固定两 worker、最新待办、token/generation、锁外外部操作及旧 observer 回归；不宣称能取消已经执行的外部 IO。
- 重启中断面试 → 无活跃工作即时门禁；不降低阈值，不清理生产数据以制造空闲。
- 合成收益与实际负载差异 → 记录本地结果、真实负载/实机验收未测范围，线上后另看 P95、错误率及用户体验。

## Migration Plan

1. 读取实际 Global Backend image/container、完整源与 Prompt、功能开关、配置/模型、Compose 身份、其它组件；保存仅服务器私有的凭据配置及不可变回退基线。
2. 将三文件最小节点迁移到实际 Global 源，运行隔离合成专项/回归、基线对照与源码保护，冻结载荷及验证证明。
3. 构建实际镜像衍生候选，运行无网络只读探针；核对路由、全部非目标文件及目标非批准节点、Global 权益/关闭开关、环境与模型。
4. 紧邻切换重新验证当前镜像和候选未漂移，全部受保护工作门禁为零后，仅替换 Global Backend；未通过即保留原服务。
5. 核对健康、restart、实际源/Prompt/路由、有效配置/模型/开关、其它组件、匿名公开入口及短时脱敏错误观察。失败时先确认当前仍属于本轮且无受保护工作，再用固定旧镜像/冻结配置回退，并复验；不覆盖后续独立发布。
6. 记录实际时间、镜像/容器/哈希、测试结果与效果边界，逐项勾选任务并严格校验 OpenSpec。没有发生的生产动作不得提前标完成。

## Open Questions

无需要用户再次确认的产品行为选择。当前实际镜像、空闲窗口和回归结果均须通过执行取得，未测结果不得作为既成事实。
