# Verification · 2026-10-08

## 本地验证

```sh
PYTHONPATH=apps/backend .venv/bin/python -m pytest \
  apps/backend/tests/test_cn_model_cutover_guards.py \
  apps/backend/tests/test_cn_shared_text_model.py \
  apps/backend/tests/test_mock_interview_generation.py \
  apps/backend/tests/test_mock_interview_rounds.py \
  apps/backend/tests/test_mock_interview_isolation.py \
  apps/backend/tests/test_web_search_chat_integration.py \
  apps/backend/tests/test_durable_material_processing.py \
  apps/backend/tests/test_chat_answer_completeness.py \
  apps/backend/tests/test_document_parser_service.py \
  apps/backend/tests/test_mock_interview_api.py \
  apps/backend/tests/test_mock_interview_readiness.py -q -rs
```

结果：114 passed、12 skipped、1 warning，1.23 秒。12 个隔离 PostgreSQL 场景未运行，原因是没有配置测试数据库；绝不使用生产数据库执行这些写入测试。Starlette/httpx 警告为既有工具链弃用提醒。

新增路由回归 6 项，覆盖摘要/模拟模型选择、摘要非思考参数、摘要失败回退、专用快答/详细覆盖保持不变以及配置与评测一致性。新增发布门禁纯单元测试 8 项，覆盖环境替换只改目标行、拒绝缺失/重复/未审阅值、非文本设置检查以及原子写入权限/冲突保护。

## 真实供应商兼容性

仅使用 [合成评测](../../../ai/evals/cn-shared-text-model-v4-1-flash.jsonl)，通过原服务适配器执行，不启动 worker 循环、不创建数据库记录、不扣费、不读取真实用户材料。

| 运行镜像 | 检查 | 本次耗时 | 结果 |
| --- | --- | --- | --- |
| backend candidate | 合成简历摘要 | 1.264 秒 | 通过 |
| backend candidate | 合成 JD 摘要 | 1.767 秒 | 通过 |
| backend candidate | 模拟首题 | 1.680 秒 | 通过 |
| backend candidate | 单题部分报告 | 4.435 秒 | 通过 |
| material-worker candidate | 合成简历摘要 | 1.586 秒 | 通过 |
| material-worker candidate | 合成 JD 摘要 | 1.629 秒 | 通过 |

这是一次有限采样，不是线上 P95、压力测试或回答质量的全面评估。摘要必须实际返回供应商结果，提取式回退不作为真实兼容成功；出题检查单题与简历事实，报告检查既有结构、原回答引用、1/10 部分练习标签与不虚构成果约束。

首次 worker 探测发现验证脚本无条件导入它不包含的模拟面试模块。只修正探测脚本为按检查范围导入后，两项 worker 供应商检查通过；没有向 worker 加入无关生产模块。

## 场景核对

- [x] Resume/JD summarized：实际两个镜像摘要均使用 v4.1，请求显式非思考，既有解析和回退回归通过。
- [x] Mock question/report：实际 backend 适配器使用 v4.1，出题/报告结构与安全断言通过。
- [x] Existing interview capabilities：快答/详细 v4.1 覆盖不变；非文本五种模型设置与切换前一致。
- [x] User work active：首次门禁检测近期准备会话为 1 时没有切换；待消失后发布前复核通过。
- [x] Idle cutover succeeds：基于实际运行镜像最小覆盖，只切 backend/worker，环境/挂载/资源限制/非目标容器不变。
- [x] Post-cutover validation failure（实现检查）：脚本具有恢复原环境/镜像并检查健康的回退分支；纯环境守卫测试通过。本次未触发故障，回退分支没有进行生产故障注入测试，不将其算作真实回退验证。
- [x] Provider verification privacy：全部供应商输入为合成数据，无用户会话/扣费，密钥仅来自服务器受限环境文件。

生产门禁和候选/上线记录保存在国服服务器 `/opt/offersteady/releases/20261008-cn-shared-text-v4-1-1`。备份含密钥，禁止把该目录全量下载或提交 Git。

## 发布后及残留风险

已于 2026-10-08 23:56 北京时间完成切换。实际运行设置和源码哈希与候选匹配。完整发布结果及 TTS 下线待办见[发布记录](../../../docs/releases/cn-shared-text-model-20261008.1.md)。

后续检查：两服务运行且重启次数为 0，backend 健康检查 healthy，启动后日志抽样没有 Traceback；原应用代码中没有旧模型字符串硬编码。`/healthz`、`/login`、公开模拟面试能力与计费状态接口均返回 HTTP 200。模拟面试仍开启，并明确无需升级助手。

真人听音、实际简历和长时多人面试体验不是本轮合成检查覆盖范围，仍需用户验收。
