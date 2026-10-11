# 国服模拟面试语音迁移 20261009.1

## 范围

用户授权替换即将下线的模拟面试朗读模型；仅国服后端。新模型 `qwen-audio-3.0-tts-plus`，音色 `longanhuan_v3.6`（龙安欢女声），端点 `wss://dashscope.aliyuncs.com/api-ws/v1/inference`。

普通快答/详细回答、截图、模拟面试出题和报告、ASR、计费、前端与助手协议不变；不部署国际服、不升级助手、不迁移数据库、不推 Git。不保证新音色与 Cherry 听感相同。

依据：[下线公告](https://www.aliyun.com/notice/118434)、[客户端事件](https://help.aliyun.com/zh/model-studio/qwen-audio-tts-client-events)、[服务端事件](https://help.aliyun.com/zh/model-studio/qwen-audio-tts-server-events)、[音色列表](https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list)。

## 实现与基线

- 既有题目走 run-task → task-started → continue-task/finish-task；二进制 PCM 仍为 24 kHz 单声道，沿用现有浏览器音频消息。
- 沿用原中文朗读指令、并发/超时/文本/音频边界、文本继续及错误脱敏。显式关闭嵌套流式生成器，取消/重播不保留连接或音频缓存；PCM 跨帧余数最多一字节。
- 旧 realtime 协议仍保留，不隐式迁移国际服。Settings 的旧默认值不代表旧模型下线后仍可用；国服三项 TTS 配置显式生效。
- 实际原后端镜像：`sha256:711cd937b57acce5c9f248ae064498ca1b751a5da608837ff225765cb18e4d00`。
- 候选镜像：`sha256:866a5e920cc8db962d9474ad3dff5995fd3348a17c3e2b2f778f9f1e43962384`，仅覆盖 `mock_interview_tts.py`，不覆盖本地其它脏文件及国际服分支。
- 服务器保密备份及发布证据目录：`/opt/offersteady/releases/20261009-cn-mock-tts-qwen-audio-plus-1`。完整环境/容器备份只在服务器，不下载、不提交。

## 自测证据

合并回归 **248 passed，0 skipped**，18.90 秒；仅有现有 Starlette TestClient 弃用警告。使用本地新建的独立 PostgreSQL 容器及分别隔离的 CN/Global 合成数据库，测试完成后容器已删除。覆盖新旧 TTS 协议、故障/错序/任务 ID/PCM/限额、取消/重播/运行时文本继续、计费/会话/助手隔离、普通回答/截图/资源清理、国际服权益隔离。

运行命令：

```bash
OFFERSTEADY_TEST_DATABASE_URL=postgresql://synthetic:synthetic-test-only@127.0.0.1:55439/synthetic_mock \
OFFERSTEADY_TEST_GLOBAL_PRACTICE_DATABASE_URL=postgresql://synthetic:synthetic-test-only@127.0.0.1:55439/synthetic_global_mock \
.venv/bin/python -m pytest \
 apps/backend/tests/test_mock_interview_tts.py apps/backend/tests/test_mock_interview_audio_tts.py \
 apps/backend/tests/test_cn_mock_tts_release_guards.py apps/backend/tests/test_mock_interview_postgres.py \
 apps/backend/tests/test_mock_interview_api.py apps/backend/tests/test_mock_interview_audio.py \
 apps/backend/tests/test_mock_interview_isolation.py apps/backend/tests/test_mock_interview_readiness.py \
 apps/backend/tests/test_mock_interview_legacy.py apps/backend/tests/test_mock_interview_rounds.py \
 apps/backend/tests/test_mock_interview_generation.py apps/backend/tests/test_global_mock_api.py \
 apps/backend/tests/test_global_mock_postgres.py apps/backend/tests/test_cn_shared_text_model.py \
 apps/backend/tests/test_chat_answer_completeness.py apps/backend/tests/test_web_search_chat_integration.py \
 apps/backend/tests/test_screenshot_inline_delivery.py apps/backend/tests/test_screenshot_stream_admission.py \
 apps/backend/tests/test_realtime_resource_cleanup.py apps/backend/tests/test_realtime_session_reclamation.py -q -rs
```

额外执行 `py_compile`、`git diff --check`、`openspec validate migrate-cn-mock-tts-qwen-audio-plus --strict` 均通过。

候选镜像通过真实适配器调用现有服务端密钥，输入全部来自合成评测文件，不创建产品会话、不扣产品积分、不保存音频：

| 合成样本 | 首音频 | 服务端完成 | 音频长度 | 音频字节 |
| --- | --- | --- | --- | --- |
| 项目介绍 | 0.553 s | 3.124 s | 7.09 s | 340320 |
| 技术追问 | 0.671 s | 3.691 s | 10.21 s | 490080 |

两段非静音、协议完整结束，第三次实际调用在首块后取消，全部连接关闭，并发名额恢复。上述仅为小样本服务端合成耗时，不是 API P95、页面播放耗时或性能承诺。

## 上线验证

预检查通过：普通进行中面试、近期准备面试、活跃页面、音频流、未完成回答、运行中的模拟面试及待执行资料任务均为 0。切换工具在修改环境前重复空闲检查；只允许重建 `compose-backend-1`，并校验其它容器标识/镜像/启动时间不变。

2026-10-09 00:59（Asia/Shanghai）切换成功。两次正式门禁均为 0 活跃任务；实际生效镜像为上述候选，三项 TTS 配置正确，其它环境配置、启动命令、宿主配置、挂载及非目标容器均未变。共享/快答/详细文本模型仍为 `deepseek-v4.1-flash`；视觉、ASR、向量、重排序模型保持原值。

上线后在实际后端进程环境中再次独立调用同一适配器：两段合成提问首音频分别 0.534 s、0.700 s，完成分别 3.045 s、3.752 s；音频字节及长度与候选探针一致，取消及全部连接关闭再次通过。这不是用户端到端测试。

公网 `/healthz`、`/login`、`/api/v1/mock-interviews/capabilities`、`/api/v1/billing/status` 均返回 200；模拟面试 enabled=true，companionUpgradeRequired=false。后端 healthy，RestartCount=0，最近启动日志 Traceback 计数为 0。证据在服务器 `deployed.json`、`backend/production-probe.json`、`post-verification.json`，没有新增产品面试记录。

## 场景核对与边界

- 同文本朗读/24 kHz PCM：协议测试及候选真实探针通过。
- 失败回退/文本继续/不新增问题及费用：运行时契约、会话及计费回归通过。
- 取消/重播/边界：单元与真实取消探针通过。
- 普通流程/国际服旧协议：回归通过，国际服线上未变。
- 空闲上线/非目标隔离/健康：正式两次门禁、运行镜像/配置校验、公网健康及非目标容器检查通过。
- 在线用户保护：保留两次门禁；有活动即拒绝切换。未为此在生产创建测试面试。
- 浏览器实际播放、真实麦克风、音色听感：待用户验收，未报告为已通过。

## 回滚

切换工具健康/配置校验失败时恢复本次前的原环境与后端镜像，不恢复或改动数据库。旧模型于公告日期下线后，旧镜像只可临时恢复代码，不保证朗读可用；应修复新模型适配并保持现有文本继续路径。
