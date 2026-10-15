# 国服模拟面试简化收费：本地验证 20261015.1

用户要求会员每日免费一场、积分 100 分一场、60 分钟自动结束，并确认适用所有有效会员。本记录对应 [OpenSpec 变更](../../openspec/changes/simplify-cn-mock-interview-billing/proposal.md) 和 [能力场景](../../openspec/changes/simplify-cn-mock-interview-billing/specs/cn-mock-flat-rate-and-deadline/spec.md)。本记录保存完成本地开发、测试及网页编译时的事实；该阶段没有部署线上、发布新的助手安装包或更改此前 1.3.5 封版。用户随后另行授权国服上线，见 [生产发布记录](cn-mock-flat-billing-20261015.1.md)。

## 最终规则

- 所有有效时间会员（日、周、月及管理赠送权益）每天免费 1 场，按北京时间 00:00 更新。仅购买积分包不产生会员免费权益。
- 免费次数用完或没有有效会员时，创建一场一次性收取 100 积分。朗读、回答、暂停、重连及报告不再收分钟费。
- 准备阶段不计时；首次成功开始后，以服务端保存的开始时间计算固定 60 分钟期限。暂停、出题等待、断线、刷新和服务重启不能延长期限。
- 到期停止收音和朗读，拒绝迟到题目及继续回答，保留已确认提交的回答并生成完整或部分报告。没有已提交回答时生成证据不足报告，不编造分数。
- 保留历史金融流水；旧的进行中场次停止新增分钟费，截止时间从原始开始时间恢复。不会自动追溯退还旧分钟费。
- 沿用原有可信故障补偿：未完成任何回答且满足终止故障条件时，仅退还实际已扣金额或恢复原业务日免费次数一次。主动取消或删除记录不退创建费、不恢复次数。
- 保留两条记录上限。普通面试、笔试、会员套餐价格与 Global 的 UTC 每日三场权益不变。

## 实现与恢复

复用账户事务锁与创建幂等键，防止免费额度并发透支及网络重试重复收费。页面按报价中的服务端业务日期安排午夜刷新，窗口重新可见或价格变化时重新报价，付费创建需要明确确认。

期限存储在原有 JSONB 记录中，无新增表迁移。控制命令、心跳、音频接收、生成任务提交及后台恢复均检查同一截止时间。到期转入报告状态会清理采集、朗读及旧题目任务；报告可在截止时间之后完成。服务重启后的待完成到期报告可恢复，真实报告生成失败仍保留手动重试。

报价新增 `dailyFreeLimit`、`durationLimitMinutes`、`nowMs`；会话公开 `startedAtMs`、`deadlineAtMs`、`durationLimitMinutes`、`endReason`。旧字段保持可读，国服 `minutePoints` 为零；页面显示固定创建费用及北京时间截止时刻。

## 已执行验证

| 验证 | 结果 |
| --- | --- |
| Backend 模拟面试、费用、期限、Runtime/API、Global、普通面试计费、Task ASR 和轻量 heartbeat | 353 passed，无跳过；1 项已有依赖弃用提示 |
| 独立 TTS 和期限任务测试 | 51 passed；已包含在上面最终回归中 |
| Web 创建报价、午夜刷新、重复请求、期限展示、收音交互、客户端与报告导出 | 43 passed，4 个测试文件 |
| Web 类型检查 | 通过 |
| Web 正式模式本地编译 | 通过；版本标识 `mock-flat-billing-local-20261015.1`，产物在 `apps/web/dist/` |
| 全量 Web 测试 | 496 passed、3 failed；失败均为下述原基线问题 |
| AI 评测文件 | 11 条 JSONL 结构与唯一 ID 校验通过，新增到期无回答/部分回答两条案例；未进行本轮真实模型评测 |
| OpenSpec、文档链接和差异检查 | 本变更 strict 校验通过；5 份 Markdown 中 6 个本地链接目标存在；`git diff --check` 通过 |

后端使用专用本机 PostgreSQL 的 `synthetic_mock_tests` 与独立 `synthetic_global_mock_tests`。会员、积分、简历及回答均为合成数据，不操作真实用户或线上账本。到期测试使用可控服务端时钟，覆盖准确边界、四个活动阶段、暂停/重连/重启、迟到模型结果、历史退款与报告恢复，没有让真实用户等待一小时。

逐项核对能力场景：每日免费及会员边界、午夜与昨日请求重试、并发与删除不返次数、固定收费及可信退款、所有活动阶段到期、离线/重启恢复、题目结果与期限竞争、页面报价刷新、Global 及普通面试隔离均有对应回归。没有修改模型或 Prompt。

## 已知基线问题与交付限制

全量前端的 3 项失败位于 [Nginx 路由契约测试](../../apps/web/nginx-release-contract.test.ts)，涉及公开 www 跳转、独立法律页面和 partner-program 路由。[Nginx 配置](../../infra/nginx/default.conf) 与该测试文件均逐字节等于本轮开始的 Git `fe17c883b1e40f55d99a8c22315340ba56574caf`；单独重跑这三项同样失败。本轮未改这两个文件，没有将这三项计为通过。

本轮没有切换生产容器或运行生产迁移，也没有替用户进行物理麦克风验收。未来上线需同步国服 Backend/Web 收费说明，并以实际运行镜像为增量基线，保留此前轻量 heartbeat、模拟面试及 1.3.5 下载清单；不能将整个本地工作区覆盖国服。Global 不需要本轮发布。

## 复核命令

```bash
PYTHONPATH=apps/backend \
OFFERSTEADY_TEST_DATABASE_URL=postgresql://synthetic_local:synthetic-local-only@127.0.0.1:55445/synthetic_mock_tests \
OFFERSTEADY_TEST_GLOBAL_PRACTICE_DATABASE_URL=postgresql://synthetic_local:synthetic-local-only@127.0.0.1:55445/synthetic_global_mock_tests \
.venv/bin/python -m pytest -q \
  apps/backend/tests/test_mock_interview*.py apps/backend/tests/test_cn_mock*.py \
  apps/backend/tests/test_global_mock*.py \
  apps/backend/tests/test_global_practice_entitlements.py \
  apps/backend/tests/test_global_practice_providers.py \
  apps/backend/tests/test_interview_usage_billing.py \
  apps/backend/tests/test_dashscope_task_asr_gateway.py \
  apps/backend/tests/test_web_heartbeat_lightweight.py
npm run test -w @offersteady/web -- src/MockInterviewPage.test.tsx src/mock-interview-client.test.ts src/mock-interview-word-export.test.ts mock-interview-release-contract.test.ts
npm run typecheck -w @offersteady/web
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=mock-flat-billing-local-20261015.1 npm run build -w @offersteady/web
npm run test -w @offersteady/web
openspec validate simplify-cn-mock-interview-billing --strict
git diff --check
```
