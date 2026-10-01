# 国服回答启动与截图异常修复 — 2026-09-25

## 范围与结果

已按用户授权完成两个确认缺陷的修复、自测，并在核查无进行中面试后，于北京时间 2026-09-25 01:18:34 完成国服 Backend 切换。未部署国际服、Web、Admin、桌面助手或材料 Worker；未改模型、Prompt、积分价格、会员门槛、音频、轮询或内存策略；无数据库迁移、用户数据修正或真实用户扣费测试。

### 回答启动错误

PostgreSQL 计费仓储的余额不足分支直接展开输入字段，将 `minimum_pass_duration_days` 等策略参数带入不接收这些字段的预约记录，造成 `TypeError`。改为显式返回预约记录支持的字段，保留余额不足业务拒绝，不绕过计费。

回归还复现了流式回答先发送 HTTP 200、后进行启动校验的问题：即使仓储修好，启动拒绝仍会成为响应已开始后的连接异常。在原专用执行器中预取首个事件，启动拒绝先返回正常 HTTP 409 错误响应；正常首个事件只发送一次，后续继续流式输出，不等待完整模型回答。没有新增一次预约或模型调用。

本轮未改前端错误文案：API 返回余额不足错误，现有前端流式入口仍可能显示“实时回答启动失败（409）”。

### 截图异常处理错误

截图后台完成操作异常后，失败状态恢复再次异常时，日志调用缺少必需的 `task`、`image_count`、`retry_count`，导致第二个 `TypeError` 掩盖原始错误。补全日志参数，分别记录原始错误与恢复错误的安全类别；不记录异常原文、截图内容、机器码或凭证。保留既有失败状态和取消规则，不声称所有第三方上传或模型失败都被消除。

## 生产基线与产物

- 旧实际运行镜像：`sha256:95f82840da434afc99c7b9c7fc76663f32acd0b4d81a2c855792372beb5385ae`。
- 新镜像：`offersteady-cn-backend:answer-errors-20260925-1`，`sha256:01d093b2469e346ba6d68cd710f0ee7f3c5860bcedd0d0cc9a85e80fa803fc50`。
- 回滚镜像：`offersteady-cn-backend:answer-errors-rollback-20260925-1`。
- 发布目录：`/opt/offersteady/releases/20260925-cn-answer-errors-1`。
- Backend 源码指针：`/opt/offersteady/backend-current` 指向上述发布目录。
- 业务 Compose 指针 `/opt/offersteady/current` 仍指向 `/opt/offersteady/releases/20260923-cn-quick-stage-1`，没有整体替换。

基于实际运行容器导出不含凭证的源码，在隔离目录应用同一补丁，并以原运行镜像为父镜像，仅复制三个生产文件。不从本地整个工作区重新构建，避免带入未授权改动。

线上 134 个 Python 文件核对结果：仅以下三个文件变化，其余旧文件均保留；候选中的 133 个文件全部匹配，旧镜像自带的 macOS 元数据文件仍保留。

| 文件（相对 `apps/backend/app/`） | 上线 SHA-256 |
| --- | --- |
| `modules/live_answer.py` | `542706aecf1ac4801767280d6776dfe542a111d29d5d606db5b37510580b148f` |
| `services/postgres_billing_repository.py` | `a85a69221334c4f45c62fc9971fd5cfb4d6235e8e1ec01b48aed99bb937d035a` |
| `services/screenshot_answer_service.py` | `0dc2bddba6da9b0c5ec93d546e75e86e75b302c3d559bfba00eeb420428ec33b` |

后续 Backend 发布必须基于实际运行镜像或 `backend-current` 合并，不得直接用旧 `current/apps/backend` 重建而丢失本次修复。Admin 继续以独立 `admin-current` 为基线；本次未改变上一轮用户搜索功能。本地保留同一增量代码，未执行 Git 提交或推送。

## 自测

- 先在旧代码上复现失败，再应用补丁。
- 本地定向回归 85 项通过，另有 foundation 回答/截图相关 14 项通过，共 99 项相关测试；不是全量 Backend 测试。
- 85 项包含 14 项隔离 PostgreSQL 集成测试，全部使用合成数据，未连接生产数据库进行写入。
- 从实际线上源码构造的隔离候选同样通过 85 项定向回归。
- 候选镜像实际依赖下离线冒烟通过：流式余额不足返回 HTTP 409；截图原始失败及恢复失败不再产生日志参数异常。未访问生产数据库、模型或 OSS。
- 覆盖普通/联网、手动/自动、流式/非流式回答拒绝；首事件顺序和不重复；执行器名额和自动回答声明释放；余额预留、幂等、结算/释放；会员门槛；截图失败恢复、恢复再次失败及取消状态保持。
- OpenSpec 严格校验、`git diff --check` 通过。

主要定向命令（需显式隔离数据库/Redis，不能使用生产连接）：

```sh
PYTHONPATH=apps/backend .venv/bin/python -m pytest -q \
  apps/backend/tests/test_answer_failure_contracts.py \
  apps/backend/tests/test_answer_failure_postgres.py \
  apps/backend/tests/test_screenshot_inline_delivery.py \
  apps/backend/tests/test_interview_usage_billing.py \
  apps/backend/tests/test_commercial_billing_persistence.py \
  apps/backend/tests/test_web_search_chat_integration.py \
  apps/backend/tests/test_live_answer_stream_executor.py \
  apps/backend/tests/test_screenshot_stream_admission.py

PYTHONPATH=apps/backend .venv/bin/python -m pytest -q \
  apps/backend/tests/test_foundation.py \
  -k 'live_answer or screenshot_answer or remote_capture'

openspec validate fix-cn-answer-and-screenshot-errors --strict
git diff --check
```

测试运行时明确设置 `OFFERSTEADY_DATABASE_URL=''`、`OFFERSTEADY_REDIS_URL=''`，以及 `OFFERSTEADY_TEST_DATABASE_URL` 指向独立本机合成测试库。临时测试库为 `offersteady-cn-bugfix-db-20260925`，只绑定本机 55439 端口，不包含真实用户数据。

## 部署门禁与验证

最终切换前即时检查：北京时间 01:18:15.026，数据库 `live` 面试 0，最近两分钟准备中面试 0；容量样本年龄 12.846 秒，活跃面试、在线面试页面、活跃 ASR 音频流均 0。只执行 Backend 的 `--no-build --no-deps` 更新，没有结束任何用户面试。

第一次切换健康检查已通过，但环境变量数组顺序改变使原哈希比较误报，自动保护回滚到旧镜像。重新逐键核对新旧镜像和实际 Compose 环境，确认无配置值变化；将检查修正为排序后比较，再次通过空闲门禁，发布同一份已测试镜像。第一次检查证据保存在发布目录 `attempt1/`，没有为绕过检查修改应用配置。

- 最终 Backend 启动：`2026-09-24T17:18:16.868338174Z`；健康状态 `healthy`，重启计数 0。
- HTTPS 首页、Admin 首页、健康接口、计费状态接口检查通过。
- 未登录会话和 Admin 接口均返回 401，鉴权未绕过。
- 环境配置排序后哈希一致；其他所有运行容器 ID 和镜像保持不变。
- 上线文件哈希与测试候选一致，且只有三个预期生产文件变化。
- 切换后短时检查的 289 行日志中无 ERROR/CRITICAL、Traceback 或 TypeError；这不是长期负载或真实用户端到端验收。

后续由用户进行普通快答、联网模式和截图回答的真实流程验收。线上未创建测试面试、调整积分或发起收费模型调用。

## Backend 独立回滚

需要回滚时先重新核查无进行中面试，再只切换 Backend，不更新所有 Compose 服务，也不变更数据库：

```sh
docker tag offersteady-cn-backend:answer-errors-rollback-20260925-1 compose-backend:latest
cd /opt/offersteady/current
docker compose -p compose --env-file .env.production \
  -f infra/compose/docker-compose.foundation.yml \
  up -d --no-build --no-deps backend
```

回滚后重新核对健康、鉴权、运行镜像和其他容器，并更新此记录，避免将 `backend-current` 误认为仍在运行版本。
