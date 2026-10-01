# 国际服联网与模拟面试 — 本地候选验收

## 状态

本文件记录 2026-09-29 上线前的本地验证，当时未修改生产。随后用户要求发布，已完成无人面试检查和国际服上线，见[生产发布记录](global-practice-production-20260929.1.md)。真实桌面助手人工验收仍待用户执行，不以合成测试代替。OpenSpec：`add-global-web-search-and-mock-interview`。

基线为实际国际服版本 `20260929-global-reliability-2`。候选在 `artifacts/global-practice-20260929/candidate/`；覆盖文件清单在同级 `overlay-files.txt`。不能发布整个主工作区：其中有其他国服变更。候选的 `core/config.py` 和 `realtime_speech_service.py` 仅手工应用新功能配置及模拟专属通道守卫，未复制主工作区其他轮询/内存改动。

## 已实现规则

- 有效、未撤销且已生效的 Global 会员，其购买时不可变套餐版本时长至少七天，可使用新功能。不是要求剩余七天；周卡最后一天仍可用。免费及日卡不可用。
- 模拟面试每日最多创建三场，UTC 零点重置；第四场提示次日再试。不收创建费、分钟费或额外联网积分。
- 每人最多保留两条进行中或已完成记录，满额手动删除。取消或删除不恢复当天次数；可信系统故障且没有提交任何回答的终止路径只恢复一次。
- 英文模拟面试：已解析简历、现有正式版助手、麦克风回答、最多十题、手动提交、真实播放状态、结束自动保存报告/评分/建议、Word 导出。首次仅验收英文，普通面试既有语言不变。
- 联网开关位于自动回答旁，默认关闭。简单回答先完成，只有详细回答使用检索；失败明确降级。关掉开关时取消旧联网任务，迟到结果不能覆盖新普通回答。
- Global 使用独立会员/配额仓储和迁移 `0052_global_mock_interviews.sql`，不读取国服钱包表；既有 Creem 价格和支付链路不改。

## 本地验证

| 范围 | 结果 |
| --- | --- |
| 独立 Global 候选后台 | 142 通过，0 跳过；包括原两批可靠性回归、Global 权益、真实隔离 PostgreSQL 并发配额及 HTTP/WS 生命周期、语音/轮次、联网退化与取消 |
| 独立 Global 候选前端 | 25 文件、158 测试通过；类型检查通过 |
| 候选生产 Vite 构建 | 通过；主包大于 500 kB 的既有体积警告仍存在，不宣称已优化体积 |
| 主工作区国服回归 | 模拟 API/持久化/生成/语音/旧助手/就绪/轮次等此前 111 通过；未部署国服 |
| OpenSpec | 严格校验通过 |
| 页面 | 创建、准备、工作台和报告的合成预览；Word 结构、Unicode、转义及导出门禁有自动测试 |

隔离 PostgreSQL 为一次性 Docker tmpfs，Global 与 CN 使用不同数据库，合成身份。Global 测试最后断言国服 `points_redemption_ledger`、`billing_time_pass_entitlements`、`billing_usage_reservations` 表不存在。没有在生产创建测试用户、面试或订单。

候选后台命令（分别将两个变量指向自己的独立测试库，禁止生产库）：

```sh
OFFERSTEADY_TEST_DATABASE_URL=<disposable-cn-db> \
OFFERSTEADY_TEST_GLOBAL_PRACTICE_DATABASE_URL=<disposable-global-db> \
PYTHONPATH=apps/backend python -m pytest \
  apps/backend/tests/test_global_practice_entitlements.py \
  apps/backend/tests/test_global_mock_postgres.py \
  apps/backend/tests/test_global_mock_api.py \
  apps/backend/tests/test_global_practice_providers.py \
  apps/backend/tests/test_global_web_answers.py \
  apps/backend/tests/test_global_first_batch.py \
  apps/backend/tests/test_global_second_batch.py \
  apps/backend/tests/test_global_usage_billing_adapter.py \
  apps/backend/tests/test_global_commerce_service.py \
  apps/backend/tests/test_mock_interview_api.py \
  apps/backend/tests/test_mock_interview_audio.py \
  apps/backend/tests/test_mock_interview_isolation.py \
  apps/backend/tests/test_mock_interview_legacy.py \
  apps/backend/tests/test_mock_interview_readiness.py \
  apps/backend/tests/test_mock_interview_rounds.py \
  apps/backend/tests/test_mock_interview_tts.py \
  apps/backend/tests/test_web_search_gateway.py -q
npm run typecheck --workspace @offersteady/web-global
npm run test --workspace @offersteady/web-global -- --reporter=dot
VITE_APP_ENV=production VITE_APP_DATA_SOURCE=backend-preview VITE_API_BASE_URL=/ \
VITE_PUBLIC_APP_VERSION=global-practice-candidate-20260929 \
VITE_GLOBAL_COMMERCE_ENABLED=true VITE_GLOBAL_COMMERCE_PROVIDER=creem \
npm exec --workspace @offersteady/web-global -- vite build
```

## 真实供应商验证

凭证始终留在国际服现有容器内；独立短生命周期进程读取现有配置，候选模块与合成样本通过内存传入，**无文件写入、无应用重启、无数据库访问**。只调用指定供应商，不扫描环境或尝试其他账号。

- `qwen3-tts-instruct-flash-realtime`，Cherry，English：国际端点成功返回音频，首段约 0.36 秒。
- 候选 TTS→16 kHz PCM→既有 ASR：约 10 秒完成测试，完整识别 `I use a unique constraint to prevent duplicate writes.`；关闭后 capture 与供应商活动会话计数归零。音频仅在该进程内存中使用，不保存。
- 当前 `deepseek-v4.1-flash`，国际端点 `/compatible-mode/v1/responses`，`reasoning.effort=none`：HTTP 200，约 5.7 秒，2 次检索、19 条供应商来源、411 字符文本。应用仍按配置限制展示来源条数。这是一次合成探针，不是延迟 SLO 或真实用户体验保证。
- 两个英文生成评测真实调用通过：简历中的密码指令未被执行，只问缓存设计；报告只引用实际提交的一段回答，标注 1/10 部分报告，没有虚构成绩。样本评分维度 65/60/35/30，服务端平均取整 48；仅为合成样本，不是实际候选人评分。
- 首次评测脚本因断言英文模板的字面词组错误失败（模板为 `unmeasured or unverified`，断言误写 `not measured`），修正测试后重新实测通过；不是生产故障。

对应工具：`apps/backend/scripts/probe_global_practice_permissions.py`、`verify_mock_interview_providers.py`、`verify_global_practice_in_memory.py` 和 `scripts/bundle-global-practice-provider-qa.mjs`。这些检查需要明确运行，可能产生少量供应商调用费用；不是自动生产监控。

官方依据：[语音区域端点](https://help.aliyun.com/en/model-studio/qwen-tts-realtime-python-sdk)、[联网 Responses 调用](https://help.aliyun.com/en/model-studio/web-search)。文档支持不等于账号已授权，以上以真实合成请求为准。

## 上线配置（后续发布已应用，见生产记录）

```dotenv
OFFERSTEADY_GLOBAL_MOCK_INTERVIEW_ENABLED=true
OFFERSTEADY_GLOBAL_WEB_ANSWER_ENABLED=true
OFFERSTEADY_WEB_SEARCH_ENABLED=true
OFFERSTEADY_WEB_SEARCH_RESPONSES_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
OFFERSTEADY_GLOBAL_MOCK_INTERVIEW_TTS_WS_URL=wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime
```

沿用现有 Global 服务端密钥即可；本次实测不需要用户提供新密钥。国服北京配置不得直接覆盖国际服。两个 Global 功能开关默认 false；未配置检索时前端禁止启用，不以反复失败冒充可用。

## 本地阶段剩余门禁（发布后的状态见生产记录）

1. 用既有 Global 正式版助手完整验证：机器码→真实麦克风→英文题目播放/停止/重播→回答提交→报告→Word；同时核验普通面试、关闭联网后的快答。
2. 检查当前线上基线没有变化；确认普通面试、准备活动、页面租约、音频和后台生成任务均空闲。
3. 准备精确 Backend/Web 镜像与配置回退，仅发布新增能力，不重建 Admin/Worker/Analytics/数据库/Redis/桌面助手。新表为增量迁移，回退时保留记录，不删表。
4. 通过门禁后才启用两个开关并部署。当前状态不能对外宣称已上线或真实助手已验收。
