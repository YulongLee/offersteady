## Context

国际服线上基线为 20260929-global-reliability-2。国服联网及模拟面试代码存在但明确绑定国服权益；不能只去掉 edition 判断。用户已确认新功能仅有效七天及以上会员可用，模拟每日三次，超额次日再试。

## Goals / Non-Goals

**Goals:** 两阶段联网、英文模拟面试/语音/报告/Word；原助手兼容；独立 Global 权益，无国服表访问；保留普通面试及支付。

**Non-Goals:** 新钱包、价格/支付/套餐版本改动、国服部署、模拟面试未经验证的多语言、普通面试限额改动、音频持久化。

## Decisions

- Global 资格由后端使用当前生效且未撤销 entitlement 及其 immutable plan version 的 duration_days >= 7 判断。剩余不足七天不失权。月卡使用购买套餐的 duration_days，不能以本次账期实际毫秒差猜测；不接受前端会员声明。
- 复用经过回归的模拟面试状态机、音频轮次与报告校验；分离 Global repository 的 quote/准入/迁移/ledger hooks。其迁移只创建模拟场次和兼容 session mode，不读取或更改 points_redemption_ledger、billing_time_pass_entitlements。国服默认 hooks 保持原行为。
- Global 创建与配额、记录槽位在 owner advisory transaction lock 下统一判断。利用持久化场次行计数，软删除只清内容，不恢复当日次数。系统/模型连续故障一题都不能完成的既有补偿路径恢复一次免费额度；取消不恢复。
- 单场资格在创建和真正开始时检查；会员到期不踢出已开始的场次，下一场再次检查。每日按 UTC，页面标明 UTC 重置。不从正常 Copilot 额度扣分钟。
- 默认关闭 Global mock rollout 标志；联网同样明确 Global feature rollout 标志。移植不得因后台开关默认值意外启用，公网 capability 不返回用户权益，用户状态必须认证。
- 使用独立英文 prompts 和评测，Global ASR frame 显式 en-US、TTS language_type=English；CN 保留 Chinese。复用头像并标明虚拟 AI。文本/播放组件独立 Global 页面，不为该功能修改助手。
- Global TTS 使用独立 `global_mock_interview_tts_ws_url` 配置，默认百炼新加坡端点；不继承国服的北京端点。密钥仍仅由服务端现有 Global 凭证或明确的语音覆盖配置提供。
- 联网复用国服安全机制但通过 Global usage adapter 检查七天会员；无国服 minimum_pass_duration 参数误传。简单回答先完成，联网只影响详细阶段；开关关闭取消旧联网任务，保留可读文本并恢复普通回答。
- 对外报错使用英文、稳定错误码，不把底层中文异常和供应商消息直接泄露给用户。对已结束报告仍允许 owner 阅读/导出，不要求重新购买。

## Risks / Trade-offs

- 共用基础 hooks 可能改变 CN 行为 → 运行原有 CN 模拟、联网及音频回归；Global 测试用没有国服计费表的独立数据库证明隔离。
- 国服 provider 可用不等于 Global 可用 → 检查 Global 配置、用合成文本验证 TTS/检索；不复制密钥，未通过不启用功能。
- UI/TTS 错把提示当答案 → 保留非回答时段音频丢弃、1.5 秒播放尾部等待、轮次 epoch 和服务端租约隔离。
- 用户在两个页面同时创建 → 原子三次配额、两条记录及幂等 key 回归。

## Migration Plan

本地在国际服独立基线制作候选包，逐文件审查差异。新增 migration 可向后兼容，不改历史套餐。验证英文页面/Word、供应商、真实设备、普通面试/支付/材料回归。部署前只读核对无 live/准备中活动/页面租约/音频/后台生成任务，保留精确镜像和配置回滚。失败关闭新功能并回滚应用，不删除新表或用户记录。

## Open Questions

无收费阻塞。UTC 和首版英文为已告知的实现选择；新语言单独验收。2026-09-29 用户要求将已自测的候选上线，真实设备测试改为上线后人工验收；该项仍未完成，不能以合成测试冒充。无人面试检查、回退准备及发布后安全检查保持不变。
