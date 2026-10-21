## Context

本轮从两服独立封版新建分支。2026-10-21只读清单显示：两服backend的共享/快答/详答为 `deepseek-v4.1-flash`，截图为 `qwen3.6-flash`；CN worker共享模型为v4.1，Global worker仍为v4。Global模拟面试及联网开关关闭，简历优化开启。百炼官方型号页确认1017支持Text/Image、Chat Completions、JSON Object及Responses web_search；组合兼容性和账号权限尚需真实探针。

## Goals / Non-Goals

**Goals:** 用当前凭据和实际适配器确认1017可接入；准备保留原功能契约的两服独立本地候选；提供成功率/耗时的有限样本和发布所需精确配置增量。

**Non-Goals:** 本轮不发布、不重启生产、不改现有.env，不创建用户会话/上传/账务任务，不推送Git，不重做前端、助手或PDF模板，不放宽简历事实/JSON守卫，不开启Global未开放功能，不做生产压测。

## Decisions

1. **先验证再实现。** 先各服对现有chat及vision端点发两项极小合成探针；失败则记录固定错误类型，不把HTTP200等同内容正确。成功后使用实际适配器做有界扩展验证，全部凭据留服务器内存，不输出完整响应、私有URL或请求标识。使用docker exec独立Python进程，禁止导入app.deps或启动真实worker。
2. **保持四字段独立。** 候选只覆盖 `OFFERSTEADY_CHAT_QWEN_MODEL`、`OFFERSTEADY_CHAT_QUICK_MODEL`、`OFFERSTEADY_CHAT_DETAIL_MODEL`、`OFFERSTEADY_SCREENSHOT_VISION_MODEL` 为1017；保留各自独立回退，避免硬编码一个全局型号。Python提供方中立默认值不变。每个worker按其实际存在字段单独准备。
3. **最小兼容补丁。** 优先纯配置；仅真实测试证明确有需要才改运行代码。Global摘要缺非思考参数时允许补显式 `enable_thinking=false`，不改变提示词、8秒超时或提取式回退。每项补丁有回归，不以忽略错误或放宽事实验证“打通”。
4. **本地验证分层。** MockTransport覆盖路由、载荷/图片顺序、流式、错误及取消语义；真实合成探针覆盖text streaming、单图/四图JPEG、CN联网、两区简历结构、CN模拟问答报告、两worker摘要。小样本记录首字/完成时间，不宣称统计P95或普遍质量优于旧模型。图像仅合成，不采集用户屏幕。
5. **部署准备与执行分开。** 保存无密钥的精确配置增量、基线镜像/源码哈希和待发布说明。本轮只生成可审阅准备材料；后续部署须最新实际镜像/环境核对、固定镜像最小overlay和所有普通/模拟/截图/资料/简历优化/账务/页面连接门禁；有活跃工作或未知状态则等待。旧脚本不原样复跑，不改current指针。

替代方案：直接改生产.env或整仓重建会跳过实测并可能回退已发布行为，故不采用；额外图片OCR再交给文本模型增加链路，与现有直接视觉回答不同，故不采用。

## Risks / Trade-offs

- [账号/地域/接口不支持] → 每服独立smoke，再测实际视觉与Responses；失败不生成“可发布”结论。
- [支持图像但四图/非思考流式组合失败] → 使用实际JPEG优化和gateway；保留旧视觉配置回退，不凭公开模态信息认定通过。
- [简历JSON、事实引用或语言退化] → 原守卫保留，真实适配器测试失败即阻止对应迁移，评测只用虚构资料。
- [统一型号配额或思考导致延迟] → 显式非思考，保留现有token/timeout预算，记录有限样本；不主动扩大超时/重试。
- [Global旧worker与backend基线不同] → 各自独立冻结/探针，不把backend镜像替换worker，不混入CN会员规则。
- [发布打断正在优化简历的任务] → 未来切换及回退门禁同时检查 `cn_resume_optimizer_jobs` / `global_resume_optimizer_jobs` queued/running及租约，不reap或清任务放行。

## Migration Plan

本轮止于本地候选与验证记录。用户晚上明确要求发布后再重新确认实际基线、备份服务器私有配置、空闲门禁双检，固定镜像与精确白名单配置overlay切换目标组件，并验证所有非目标设置/路由及健康；失败恢复受同等门禁与归属保护，不删除数据卷。

## Open Questions

无产品决策待确认。账号权限、组合接口兼容性、耗时/质量属于必须记录的验证结果；未通过的能力不得标记为已完成或可发布。

## 2026-10-21 国服发布阶段追加

用户后续已明确授权国服模型替换与20MiB上传修复一同测试、部署。前文非目标及迁移计划中“本轮止于本地”仅描述已完成的最初阶段；这次生产阶段只覆盖国服，不扩展到国际服或助手，不回写旧探针和未部署记录。

国服模型发布采用各组件自身固定运行镜像，Backend只变更 `OFFERSTEADY_CHAT_QWEN_MODEL`、`OFFERSTEADY_CHAT_QUICK_MODEL`、`OFFERSTEADY_CHAT_DETAIL_MODEL`、`OFFERSTEADY_SCREENSHOT_VISION_MODEL` 四个既有环境键；material-worker只变更前三个既有键。旧镜像、完整私有环境和运行参数在服务器内保留用于核对和回退。模型之外的环境、端点、挂载、网络、命令、业务/Prompt输入和非目标组件不得变化。国服无模型兼容源码补丁。

同批网关变更独立依据实际运行Nginx配置制作窄范围上传规则增量，遵循 `fix-material-upload-proxy-size-limit` 的产品20MiB和multipart边界验收，不把仓库完整Nginx或网页静态替换到线上。

门禁必须在切换前重复执行并处理新工作进入的竞态，不能只复用此前的空闲快照。必须覆盖现有普通/模拟面试、准备/页面lease、音频/连接、未完成文字/截图、资料processing/deletion/reconcile、`cn_resume_optimizer_jobs` queued/running/有效claim租约，以及未完成账务；未知状态拒绝切换。不能通过取消、回收或清理真实工作放行。失败回退也应用相同工作保护及配置归属检查。

验收使用有效Settings和容器配置差异白名单、完整运行源码输入哈希/路由清单、健康与短期脱敏错误。若需要再次调用真实模型，仅可复用有界的合成探针，不创建产品会话/资料任务/扣费。少量CN截图样本已有长尾，功能接入通过不等于性能提升；保留独立视觉模型配置供受控回退。

## 2026-10-22 发布前账务门禁语义校正

第一版新门禁把所有 `billing_usage_reservations.status='reserved'` 当成执行中的账务，实际只读发现22条 `answer` 预留均超过7天和实际TTL、早于原Backend进程出生，关联用户没有进行中的会话。库存预留与执行工作不能等同：`BillingService.reserve_usage` 在读取既有预留前先按用户惰性释放过期预留；离线后没有再次访问的用户可能保留历史库存。回答生成及结算只在Backend同步调用/进程内线程执行，资料worker没有可恢复的answer作业。因此已超过TTL且早于当前原进程出生的answer库存不可能仍拥有原执行线程；新请求重放又会先执行既有TTL释放。

以独立 `20261021-cn-upload20m-model1017-2` 目录、`_v2` 控制器和 `_r2` 支持包修正这个新增门禁的分类，完整保留第一版源码、input与prepared证据。仅 `usage_kind='answer'`、`created_at_ms>0` 且严格早于 `min(now-effectiveTTL, 原BackendStartedAt)` 的reserved库存记为信息。实际TTL与业务一致为 `max(60, int(settings.billing_usage_reservation_ttl_seconds))`。原Backend出生时间从新鲜安全基线的Docker UTC纳秒时间戳整数派生并绑定input/manifest，与冻结原容器Id/StartedAt逐次核对；切换后不使用新容器出生时间扩大分类。缺失/非法/漂移时拒绝放行。

所有当前/未过TTL/未知或其它usage类型预留、索引预留、订单/回调保护不变，全部普通/模拟/页面/音频/任务/资料/简历优化门禁及最后TCP检查不变；准备页lease仍会独立阻止切换。这是对“预留库存不等于执行”的校正，没有清理、释放或结算任何真实记录，也没有修改收费或余额。
