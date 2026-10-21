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

## Global authorized production phase - 2026-10-22

Freeze each actual Global image, complete runtime manifest, effective Settings, Compose/environment/Config/HostConfig/mounts/networks and non-target identities. The approved baseline images are Backend sha256:f6a4dad4fb27222ca79f1fb5a86c23267093c741b4536c64ca76b83ac096ec19 and worker sha256:73624b44e619f6090249798047701c59ed0381d793c1302b59078349707f3010. Reject drift. Independently patch each original document_processing.py with exactly one enable_thinking=False payload line bound to its before/after SHA; never replace worker with Backend. Keep the eight-second summary budget and extraction fallback. Only Backend four existing selectors and worker shared selector change. Web static and Nginx are non-targets.

Prepare/preflight/each component cutover/recovery require fresh ordinary/mock/preparation/companion/audio/connection/answer/screenshot/material processing/deletion/reconciliation/Global optimizer queued-running-valid claims/Global financial checkout-callback-reservations and Backend TCP gates. Inspect actual Global storage semantics rather than CN assumptions. Active or unknown work defers without terminating or clearing work. Journal created ownership durably; recover only proven release-owned components using pinned original image and environment, guarded by the same work checks; never overwrite later actor drift.

No-network actual-image probes verify the full file tree, exact Settings allowlist, complete routes/OpenAPI. Preserve English/languages, Creem, UTC entitlements, resume daily once, disabled mock/search flags, all74 prompts and multiscreen behavior. Independently verify production and observe short sanitized ERROR/traceback/HTTP5xx counts. Raw logs/config/secrets stay server-side. Synthetic durations cannot establish production P95.
