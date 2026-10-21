# 国服1017模型 · 生产授权后的本地复核

## 状态与授权

用户于2026-10-21后续明确要求，将简历上传20M修复和今天已验证的模型替换一同测试、部署到国服。本记录是此次国服发布前的本地复核，**不代表已经部署**；实际切换和验收由发布控制器另行记录。

原[本地验证记录](model-1017-local-20261021.md)和原供应商探针均保留其当时“未部署”的真实状态。新增授权见[Proposal追加](../../openspec/changes/unify-models-v41-flash-1017/proposal.md)及[能力Spec](../../openspec/changes/unify-models-v41-flash-1017/specs/verified-model-1017-routing/spec.md)。同批上传修复由[独立变更](../../openspec/changes/fix-material-upload-proxy-size-limit/proposal.md)管理，本模型复核不修改网关工具、网页源码或静态包。

## 精确配置复核

工作区 `/private/tmp/offersteady-cn-model-1017-20261021`，分支 `codex/cn-model-1017-20261021`，来自封版 `release-cn-20261019.2` / `19fdf593b1ef0e574247fa602bb4de3b8e3b6d2e`。

| 组件 | 允许变更的既有环境键 | 新值 |
| --- | --- | --- |
| Backend | `OFFERSTEADY_CHAT_QWEN_MODEL`、`OFFERSTEADY_CHAT_QUICK_MODEL`、`OFFERSTEADY_CHAT_DETAIL_MODEL`、`OFFERSTEADY_SCREENSHOT_VISION_MODEL` | `deepseek-v4.1-flash-1017` |
| material-worker | `OFFERSTEADY_CHAT_QWEN_MODEL`、`OFFERSTEADY_CHAT_QUICK_MODEL`、`OFFERSTEADY_CHAT_DETAIL_MODEL` | `deepseek-v4.1-flash-1017` |

[模型overlay](../../infra/compose/docker-compose.model-1017.cn.yml)恰好包含上述七个键，无endpoint、凭据、图像上限、费用、开关或镜像变更，SHA-256为 `f0ee5742c79badd1e4b019c86dfc93e93031e163c69113689381dcce0b9d75e3`。国服模型候选没有运行源码补丁；Backend业务源码、Prompt和Web源码相对封版标签的tracked差异为空。ASR、TTS、embedding、rerank和MinerU保持原配置。各组件仍需使用其自身实际固定镜像，不能用Backend镜像代替旧worker。

结构化复核见[scope-review.json](../../artifacts/cn-model-1017-release-20261021/scope-review.json)。此项仅验证本地候选范围；线上完整私有环境、挂载、命令和网络差异仍须由发布前的新鲜实际基线白名单核查。

## 本地测试结果

2026-10-21 23:34 CST完成24个相关文件的整组回归：**739 passed，0失败，0跳过，72.45秒**。仅有既有Starlette TestClient弃用警告。测试使用本机合成PostgreSQL和独立临时数据库，临时数据库在本次运行结束后清理；简历测试也仅使用既有专用合成数据库及每例独立schema。没有访问生产数据库、读取真实资料、创建真实用户工作或调用真实模型。

覆盖1017路由/流式非思考/输出完整性、单图与四图及截图准入、简历JSON与事实守卫/部分修改/真实账务/每日三次权益/退款、模拟面试生成/API/并发/60分钟截止/计费，以及普通面试计费。

执行入口：

```sh
/Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python /private/tmp/run-cn-model-1017-release-tests.py
```

入口内以 `PYTHONPATH=apps/backend` 执行 `python -m pytest -q --tb=short`，完整24文件清单及本机独立合成数据库建立/清理逻辑保存在[执行脚本](../../artifacts/cn-model-1017-release-20261021/run_local_tests.py)。结果见[local-tests.txt](../../artifacts/cn-model-1017-release-20261021/local-tests.txt)。这些测试与最初候选430/155项及真实探针有重叠，不相加宣称独立测试数。

复核过程中两项中间情况保留为明确限制，未当作产品测试通过：

- 首次加入封版遗留 `test_mock_interview_generation_diagnostics.py` 时，因其引用封版不存在的 `app.services.mock_interview_diagnostics` 而收集失败；没有为了通过测试恢复已撤回源码，也没有宣称整个仓库所有测试通过。
- 随后的18文件整组在sandbox内557项通过、22项因禁止访问本机TCP数据库而setup错误；确认仅本机合成库后以受控权限重跑并扩展至上述24文件，最终739项全部通过。该环境错误未冒充模型失败或静默跳过。

`openspec validate unify-models-v41-flash-1017 --strict`通过；最终发布前应对合并后的规范再次校验。

## 真实供应商证据及其限度

核对既有 `artifacts/model-1017-20261021/verification-summary.json`：按国服去重的实际适配器最终证据为13项，全部通过，覆盖快答/详答、单图/四图、简历有/无JD、模拟出题/报告、Backend与独立worker的两类摘要，以及Responses实际搜索。原失败记录没有删除或改写；初始严格格式失败及搜索来源约束问题的复测说明仍在原本地记录。

少量合成题只证明当前凭据和协议组合可用，不能证明所有真实内容质量或生产P95。国服1017四图完成样本约14.34秒与5.293秒，单图约6.872秒与10.593秒，已有波动，不能承诺截图普遍提速。原事实/完成性守卫和超时预算不放宽；独立视觉模型配置保留，可在归属与用户工作门禁通过后单独恢复原值。

## 生产验收要求

发布前及实际切换前重新核对实际镜像、完整环境/运行输入与配置归属，并重复全部用户工作门禁。除普通/模拟面试和页面/音频/连接、未完成文字/截图、资料作业和账务之外，必须检查 `cn_resume_optimizer_jobs` 的queued/running及有效claim租约；未知状态拒绝切换，不取消/回收用户工作来放行。

切换后核对Backend四键、worker三键的有效Settings与容器环境；所有非白名单配置、业务源码输入、Prompt、路由、会员/积分及现有截图单图/最多四图行为必须保持。验收健康和短期脱敏错误，记录新容器实际归属。若需真实调用验证，只允许有界合成探针，不建立真实会话、上传或账务；不将HTTP200单独视为完整业务通过。

本代理仅完成本地复核和规范追加，未SSH、未部署、未提交或推送Git。国际服及助手不在本次发布授权范围。
