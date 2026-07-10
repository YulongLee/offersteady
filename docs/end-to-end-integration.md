# OfferSteady 全链路联调说明

状态：Active

这条联调线用于在不改变已批准产品原型交互的前提下，串联真实环境中的主要业务链路，并生成可回放的 Integration Report。

## 联调覆盖范围

- 注册 / 登录
- Resume 上传
- JD 上传
- Knowledge Base 上传
- OSS 上传
- Document Processing Pipeline
- Interview Session
- Live Answer
- Screenshot Answer
- Realtime Speech
- Conversation Storage
- Interview History

## 前端联调模式

前端原型结构不变，产品运行时始终读取 Backend API：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev:web
```

这样页面仍保持已批准的产品原型交互，但数据来自后端真实 API。如果核心页面还没有真实后端状态接口，页面会直接显示联调失败提示；这类失败会被视为真实问题，而不是“演示成功”。

## 后端联调命令

仅跑场景编排：

```bash
cd apps/backend
python -m app.services.end_to_end_integration --skip-providers
```

先验证第三方就绪，再跑完整联调：

```bash
cd apps/backend
python -m app.services.end_to_end_integration
```

或使用安装后的脚本：

```bash
offersteady-run-e2e
```

## 报告输出

默认输出到：

```text
artifacts/integration-reports/<report-id>/
  report.json
  report.md
  bug-list.json
  bug-list.md
  todo-list.json
  todo-list.md
```

报告拆成两层：

- Provider readiness：第三方与基础设施是否通过
- Scenario readiness：业务场景是否完整闭环
- Triage outputs：本次联调暴露出的 Bug List 与 TODO List

失败归因会标注为以下几类之一：

- `frontend-api-mode`
- `backend-orchestration`
- `provider-or-infrastructure`
- `environment-or-seed-data`

## 联调数据边界

- 只允许使用合成或脱敏 Resume / JD / Knowledge / Screenshot / Audio
- 不要把真实候选人资料放进联调脚本、日志或报告
- 真实第三方调用会产生费用，尤其是 DashScope 与 MinerU

## 故障排查建议

1. 先跑 `python -m app.services.integration_verification --list`
2. 先单独验证 OSS、PostgreSQL、pgvector
3. 再验证 MinerU、Chat、Vision、Embedding、Rerank、Realtime ASR
4. 第三方全部就绪后，再跑 `python -m app.services.end_to_end_integration`
5. 如果前端页面直接报错，优先检查是否仍缺少核心聚合状态 API 或本地测试账号数据，而不是恢复本地演示数据兜底
