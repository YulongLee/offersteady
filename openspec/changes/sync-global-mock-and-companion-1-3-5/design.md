## Context

状态：apply-ready；用户明确授权测试通过后国际服上线，并确认国际服收费保持。关联已验证的 [收音与换题修复](../fix-mock-local-audio-and-turn-latency/proposal.md)。实际 Global Backend 是 20261011 性能同步镜像，三平台清单仍为 1.3.2；运行 Web 与 future/latest 标签可能不同，必须核对实际组件。

## Goals / Non-Goals

**Goals:** Global 换题不等待旧 ASR 关闭、清理有界且轮次隔离、可安全定位生成故障；三平台正式 Global 1.3.5 及可靠元数据；保留已发布 Global 功能和性能。

**Non-Goals:** Global 收费/UTC 三场/七天会员准入或单场时限变更、现有模拟面试开放开关变更、新钱包、支付/模型/Prompt/语言政策变更、国服部署、原始音频持久化、安装包之外的真实用户测试或权限重置。

## Decisions

1. 以运行容器镜像为基线提取纯源码，使用已验证 pre-CN-fee 修复方法做最小差异；不使用整份混合工作区或未启用 latest 标签。候选只覆盖审核通过的文件，并检查既有 heartbeat/P95、Global 准入与支付不变。Global Web 若有已验证但未生效的性能候选，必须证明与实际运行资产的差异仅在获准性能范围并复测后才能使用。
2. 旧采集先撤销 epoch 和回调，独立 4 个关闭工作线程跟踪到实际 provider 释放；活动与关闭总数仍限制在现有 64 上限。不能用无界后台线程、忽略 cleanup 异常或让新轮共享旧 provider。
3. 生成诊断仅记录固定阶段、耗时、随机诊断 ID 和允许的错误类别/HTTP 状态；不改实际模型请求内容、Prompt、重试次数和故障退款语义。共用 provider 保持可替换，Global 端点和英文配置沿用实际值。
4. 客户端使用独立 Mac/Windows 源快照，避免共享 dist 构建竞争；Global immutable runtime resource 决定运行地址与稳定用户身份。共用代码保留开发环境 override，但正式有效配置始终为 Global HTTPS，无本地测试资源或服务端凭据。
5. Global Mac 管线显式选择 production entitlement/sign hook、公证及 App/DMG 终检；原生 helper 使用 Global 稳定身份和英文 usage declarations，保留 CN 默认 plist 与 CN/Beta 构建行为。元数据从实际已验证产物生成，不能仅按平台猜测 notarized/verified。Windows 沿用当前 unsigned 分发状态，验证 NSIS 载荷及实际 x64 PE。
6. 三平台全部终检后上传既有 Global 对象存储的不可变 1.3.5 命名空间，完整读回校验再统一发布清单。保留原清单和旧对象；服务端源码候选必须携带本次 Global 清单，防止后续重建恢复 1.3.2。
7. 发布使用私有服务器备份、精确环境/Compose/镜像校验、即时用户工作门禁和失败回滚。只切换需要更新的 Global Backend/Web；Admin/worker/数据库/Redis、国服均保持。无数据迁移；不复制任何国服凭据或钱包记录。

## Risks / Trade-offs

- Global 共用基类受国服费用代码污染 → pre-CN-fee 合并和独立 Global PostgreSQL（无国服钱包表）回归，超过 60 分钟仍可继续原流程。
- 慢关闭占满资源或取消观察任务丢 cleanup → 有界独立执行器、实际关闭追踪及并发/取消回归。
- 构建/下载包串服或生成错误元数据 → final asar/resource 验证、实际签名和完整对象校验；不使用“搜到 CN fallback 字符串”代替有效配置验证。
- 低磁盘预算或构建失败 → 先检查实际资源、仅构建增量和三个产物；不擅自清理历史镜像/用户文件，失败保留可诊断材料。
- Web 独立分包兼容 → 若需要更新，使用实际基线且保留旧 hash、CSP/路由/会员页面；以完整浏览器运行验证，静态图校验不能替代模块真正导入。

## Migration Plan

源快照、开发与合成回归 → 正式安装包/候选镜像/浏览器验证 → Global 不可变安装对象上传及读回 → 即时门禁与组件切换 → 公开清单/下载/入口/健康及配置不变核验。回滚恢复旧应用镜像和清单，不删库、删表或删安装对象。物理 Windows/Intel Mac 麦克风等无法代替用户验收，交付明确实际完成范围。

## Open Questions

收费问题已解决：用户选择保留国际服现有收费，仅性能、收音和稳定性优化。实际 Web 使用 `aa40…` 镜像，未使用 future 镜像；只加入经过源码及真实浏览器验证的状态请求协调和三平台下载元数据增量。公开模拟面试能力开关原本为 false，本轮保持原值；本地合成启用验证不能表述为线上开放。
