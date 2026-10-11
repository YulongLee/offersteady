# 国服共享文本模型统一 · 2026-10-08

## 结果与范围

2026-10-08 23:56（北京时间）已切换国服 backend、material-worker。两者共享模型 `OFFERSTEADY_CHAT_QWEN_MODEL` 从 `deepseek-v4-flash` 更新为 `deepseek-v4.1-flash`。既有快答、详细回答覆盖本来就是 v4.1，保持不变。

因此国服快答、详细回答、模拟面试出题/报告、简历/JD 面试摘要统一使用 v4.1。资料摘要只新增显式 `enable_thinking=false`；原提示词、结构解析、8 秒超时与提取式回退不变。

未修改国际服、桌面助手、前端、计费/会员、数据库内容、ASR、TTS、截图视觉模型、embedding 或 rerank。不要求用户升级助手。

变更规格：[unify-cn-text-model-v4-1-flash](../../openspec/changes/unify-cn-text-model-v4-1-flash/proposal.md)。验证明细：[verification](../../openspec/changes/unify-cn-text-model-v4-1-flash/verification.md)。

## 发布基线与方式

不是从历史发布目录或整个本地工作区重建。候选镜像直接派生自检查时正在运行的镜像，唯一新增代码层是原 `document_processing.py` 中的一行非思考参数。

| 服务 | 基线镜像 ID | 已部署候选镜像 ID |
| --- | --- | --- |
| backend | `sha256:c0079e2b858dff40d0bb7d8353a36ba44eab1fff72946ee33194d755527b98c5` | `sha256:711cd937b57acce5c9f248ae064498ca1b751a5da608837ff225765cb18e4d00` |
| material-worker | `sha256:9d99eaf8f496a00524c6960336959efbcc6294c16b4e4b857f464403d391d21b` | `sha256:df6b8500500e955aa2f01c3bc0c5b40dab218296459f4e8341da268bb6b0ee43` |

沿用每个容器自己的 Compose 文件和发布根目录，只重建这两个服务的容器；没有重建 PostgreSQL、Redis、前端、后台管理或其他服务。全部运行环境逐键比较，仅共享文本模型键不同。启动命令、资源限制、挂载、健康检查和非目标容器 ID/镜像/启动时间均验证不变。

现有发布指针保持不变，因为本次目录仅是最小覆盖与验证记录，不包含可替代完整发布目录的全部资源。后续部署必须以实际运行镜像/配置为基线，不能仅凭 `current` 指针重建而覆盖本次更新。

## 门禁和验证

切换前连续两轮门禁均通过：普通进行中面试、近期准备会话、活跃页面/音频、未完成回答全部为 0；模拟面试仅有已完成记录；资料处理、删除、对账作业无待处理或运行任务。

另外发现 7 条历史 QUEUED 任务与已失败的持久作业状态不一致，最近更新已超过 17 天。它们不属于当前执行工作，本次未删除或修正记录。门禁仍阻止任何活跃持久作业及非历史失败对应的非终态任务。

- 本地回归：114 passed、12 skipped。跳过项均需要未配置的隔离 PostgreSQL 测试数据库；不是已验证的数据库端到端场景。另有既有 Starlette/httpx 弃用警告。
- 真实供应商：使用合成数据，backend 镜像验证摘要 2 项、模拟出题/报告 2 项；独立旧版 worker 镜像验证摘要 2 项。共 6 项通过，没有创建用户会话、扣费或保存真实个人资料。
- 发布后检查运行模型、候选源码哈希及健康状态；健康接口与公开基础能力接口可访问。
- OpenSpec 严格校验及改动空白检查通过。

## 实际模型

国服 backend：

| 用途 | 模型 |
| --- | --- |
| 共享文本、快答、详细回答 | `deepseek-v4.1-flash` |
| 模拟面试朗读 | `qwen3-tts-instruct-flash-realtime`（本次未改） |
| 截图 | `qwen3.6-flash` |
| ASR | `qwen-audio-3.0-asr-flash-streaming` |
| embedding | `text-embedding-v3` |
| rerank | `qwen3-rerank` |

独立 material-worker 的三个文本模型设置均为 v4.1。其旧版 Settings 没有模拟面试 TTS 字段；不补入与其职责无关的新模块。

## 回退与后续风险

配置备份、原容器检查、基础镜像、候选镜像、供应商探测和上线记录只保存在国服服务器 `/opt/offersteady/releases/20261008-cn-shared-text-v4-1-1`。包含密钥的原环境和检查信息仅在服务器受限目录内，不进入 Git，不下载或展示。

发布脚本在健康/配置检查失败时恢复原环境和基础镜像，仅切回目标两服务，不恢复或删除数据卷。本次没有触发回退。由于旧共享模型将下线，使用 v4 回退仅是 2026-10-10 下线前的临时措施。

重要：百炼[模型下线公告](https://www.aliyun.com/notice/118434)还列出 `qwen3-tts-instruct-flash-realtime` 将于 2026-10-10 下线，模拟面试朗读仍需单独迁移；本次文本模型统一不解决语音风险。

本次未推送 Git。用户仍需进行普通快答、资料解析、模拟面试出题/报告的实际体验验收。
