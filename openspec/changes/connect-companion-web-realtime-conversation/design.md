## Context

当前仓库已经具备桌面伴随助手、机器码绑定、后端 Realtime Speech 服务和网页实时面试页，但这些模块仍停留在“存在接口、不保证当前 session 真实贯通”的状态。用户进入面试页后，桌面端采集到的“我 / 面试官”语音并没有稳定地进入网页左侧实时对话区，导致产品最核心的使用链路没有完成闭环。

这次变更不调整产品原型布局，只补齐一条严格依赖当前面试 session 的实时数据链路：桌面端采集双通道音频，后端按 source kind 路由为两类转录，网页端只消费当前 session 的转录并展示为“面试官 / 我”。

## Goals / Non-Goals

**Goals:**

- 让桌面伴随助手的 `microphone` 和 `system` 双来源音频进入当前面试 session 的 Realtime Speech 链路。
- 让后端将 `microphone` 路由为“我”、`system` 路由为“面试官”，并输出当前 session 可消费的转录。
- 让网页实时对话区优先展示当前 session 的真实双角色转录，而不是占位或历史残留数据。
- 为实时链路增加分层诊断，区分设备采集、上传、ASR、网页消费和绑定状态问题。

**Non-Goals:**

- 不修改网页实时面试页的布局结构、分栏方式和视觉风格。
- 不在本变更中重做 native macOS 音频采集内核本身；若 native runtime 未就绪，本变更只定义链路契约和消费逻辑。
- 不在本变更中实现新的 ASR 供应商耦合逻辑或保存原始音频。

## Decisions

### Decision 1: Treat current session as the only source of truth for realtime conversation

网页实时对话区只读取当前面试 session 的实时转录、问题候选和设备状态，不再允许通过“最新一条”“上次绑定设备”或跨 session 聚合来推断显示内容。

Alternative considered: 继续从全局聚合状态读取最近记录。缺点是非常容易把历史转录或旧绑定带进当前面试页。

### Decision 2: Keep dual-channel role mapping at the backend boundary

桌面端只负责声明 `sourceKind` 为 `microphone` 或 `system`；“我 / 面试官”的业务语义由后端 Realtime Speech 服务统一决定并写入 transcript role。这样网页端只消费统一角色，不承担设备来源判断。

Alternative considered: 在网页端根据 source kind 自行判断角色。缺点是前后端语义容易漂移，且历史记录、快答和后续检索都需要重复映射。

### Decision 3: Live conversation rendering SHALL degrade by diagnostic stage, not by silent fallback

当链路断在采集、上传、ASR 或网页消费任一阶段时，系统必须保留当前 session 的阶段性状态，而不是简单回到空态。这样用户能知道“桌面端没收上来”还是“后端没转出来”。

Alternative considered: 统一显示“暂无实时对话”。缺点是用户无法判断问题出在桌面、后端还是网页。

### Decision 4: Companion publishing and local monitoring stay loosely coupled

桌面端在 live session 中，只有当发布链路已经产出可用健康状态后，才能完全接管本地监测显示。否则页面继续展示本地检测结果，避免“已进入面试后整块波动条熄灭”的体验。

Alternative considered: 一旦进入 live 立即停止本地检测。缺点是发布链路启动失败时，用户会误以为麦克风和电脑输出彻底失效。

## Risks / Trade-offs

- [Risk] 当前 native runtime 仍未完全产出稳定双通道帧 → Mitigation: 本变更明确链路契约和消费规则，同时保留本地监测回退显示，避免完全黑盒。
- [Risk] 后端已有历史 transcript/event 数据污染当前页面 → Mitigation: 所有网页消费都强制带当前 `sessionId` 和当前用户上下文。
- [Risk] 设备绑定已存在，但 live conversation 仍无内容，用户难以定位 → Mitigation: 增加按阶段分类的 runtime diagnostics，并在网页空态时优先显示当前 session 诊断原因。
- [Risk] 双通道 source kind 与 transcript role 出现语义漂移 → Mitigation: 角色映射只保留在后端一处，协议层只传 `sourceKind`。

## Migration Plan

1. 明确并固定桌面端双通道发布契约：`microphone` 发布“我”，`system` 发布“面试官”。
2. 调整后端 Realtime Speech runtime，只返回当前 session 的实时转录、候选问题和分阶段诊断。
3. 调整网页 live 页面，优先渲染当前 session 的双角色转录，并把空态与错误态绑定到当前 session 诊断。
4. 调整桌面端健康状态接力逻辑，避免进入 live 后立即失去本地波动反馈。
5. 增加回归测试：当前 session 转录显示、跨 session 过滤、publisher 启动失败时本地波动保留、快答只消费当前 session 最近的面试官文本。

Rollback:

- 若真实发布链路尚未稳定，网页仍可以保留当前布局，但必须明确显示“当前 session 未收到实时转录”，不能误展示历史数据。
- 若桌面发布链路回退，本地监测显示不得被关闭。

## Open Questions

- 当前 live 页面最终是继续用轮询拉取 `transcripts/candidates/events`，还是补一个当前 session 的轻量推送通道更合适？
- 快答触发是否只取最近一条“面试官”最终转录，还是允许基于最近若干条同 session 面试官转录做问题拼接？
- 当桌面端只成功采集到单通道时，网页是否继续显示单角色实时对话，还是强制提示“未完成双通道接入”？
