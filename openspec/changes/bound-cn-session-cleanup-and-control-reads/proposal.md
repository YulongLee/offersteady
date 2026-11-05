## Why

国服2026-11-04下午6–7场并发面试下API P95约793ms，且结束/连接存在12–27秒长尾。实际a1e6版本仍有按用户查询前扫描全站历史绑定的路径；慢资源关闭也与新连接准备共享处理容量。用户授权本地优化、自测，晚上另行通知部署。

## What Changes

- CN结束单场按owner/session定点处理绑定；用户设备列表使用owner作用域索引，避免全站读取后过滤，并覆盖旧数据初始化和退役/TTL/重启。
- CN普通实时语音逻辑关闭与物理WebSocket关闭分离，使用有界、可排空的关闭执行器；新连接准备使用独立有界通道，保留同场串行、权限、计费、退役和晚到结果保护。
- CN无正文性能回执使用权威轻字段校验并避免无效DEBUG序列化，不改回执次数、字幕频率或鉴权缓存期限。
- 从当前实际版本的封存237输入构造本地候选，做真实本地Redis、PostgreSQL、历史规模和混合并发回归，保持完整合同及非目标。

## Capabilities

### New Capabilities

- `cn-owner-scoped-runtime-reads`: 用户作用域索引及单场定点清理。
- `cn-bounded-provider-close`: 有界物理关闭、逻辑退役与准备通道隔离。
- `cn-lightweight-performance-ack`: 无正文回执的轻量授权读取。
- `cn-cleanup-load-verification`: 实际基线、合成规模和混合负载验收。
- `cn-cleanup-control-production`: 11月6日追加授权的实际增量发布、空闲/归属保护及生产验收。

### Modified Capabilities

无既有产品功能、收费或模型规则变更。

## Impact

仅CN Backend相关仓库、service、实时执行器和普通ASR可选关闭能力。保持Web/助手1.3.6/Global/worker、模型/Prompt、计费、配置、依赖、SQL结构/连接池和API合同。不读取真实用户资料到测试，不持久化音频/正文。只在本地开发自测，不SSH、构造生产镜像、部署/重启、生产压测、真实模型/面试/付款、提交或推送Git；后续部署需用户指令并重新审查实际基线。

## 2026-11-06 production authorization

用户现已明确要求部署国服并自行测试。上述只本地约束描述11月4日已完成阶段；新增生产阶段仅允许新鲜只读核对、固定七文件增量镜像/隔离合成探针、完整空闲/归属门禁后的CN Backend切换和验收。继续禁止其它组件/国际服/模型/计费/配置/依赖/SQL/池更新、真实用户测试数据/模型/面试/付款/生产压测、强停用户工作、提交推送Git。范围、失败恢复与保护见新增production spec。
