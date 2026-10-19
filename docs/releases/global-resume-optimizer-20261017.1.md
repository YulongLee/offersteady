# 国际服简历优化发布 — 20261017.1

**2026-10-18 00:00:00.465（Asia/Shanghai）已完成 Global Backend/Web 发布，00:01:25.259 独立 verify 通过。** 本版本沿用 `20261017.1` 发布编号，实际切换日期为 10 月 18 日。用户可从[国际服简历优化](https://offersteady.com/app/resume-optimizer)进入，登录有效时间会员账号测试。

相关[需求](../../openspec/changes/add-global-resume-optimizer/proposal.md)、[最终合同](../../openspec/changes/add-global-resume-optimizer/contract.md)、[本地验收历史](global-resume-optimizer-local-20261017.1.md)及[46 个场景验证记录](../../openspec/changes/add-global-resume-optimizer/verification.md)。本轮只发布国际服；国服、Admin 和 Windows/macOS/Linux 伴随程序不发布，不提交推送 Git，不归档 OpenSpec。

## 已发布行为

- Global 有效付费时间会员（含 1 天套餐）UTC 每日免费优化 1 次；非会员提示升级，当日用完次日再试。没有积分、新钱包或单次购买入口，现有其他会员权益、Creem、分钟和模拟面试配额保持。
- 选择或沿用既有上传流程提供自有 ready 简历，可添加目标岗位和 JD。提供参考评分、原文依据、修改建议、缺失事实提示、保留原内容的优化稿，用户可对照编辑并下载真实 Word/PDF。评分不代表录用概率，下载/另存前需确认事实。
- 兼容既有 MinerU 受控 HTML 表格，转换只发生在优化输入副本，保留单元格文字、数字、日期和联系方式。原文件、Parser 产物和旧面试快照不修改；不支持或可执行 markup 在次数预留/模型前明确拒绝。
- 独立有界任务与模型客户端，不使用实时回答执行池；每账号 1 个未完成、全局最多 8 个未完成/1 个模型请求。失败/取消释放创建日次数，编辑、下载、另存不重复占用。取消/删除阻止迟到结果复活；删除源资料会清理派生任务内容，显式另存的独立简历保留自身删除控制。

## 固定镜像及发布身份

| 项目 | 实际已核验值 |
| --- | --- |
| 原 Backend 镜像/固定回退 | `sha256:c0503cb8a166dc4cfb64e3d4ca1f98792e788cdb29147d8282a8e43d0146726a` |
| 原 Web 镜像/固定回退 | `sha256:ab7706981124579a9fb6e703702202c299817af1a78330068637bd7ba6eaca0c` |
| 已发布 Backend 镜像 | `sha256:991cabbc65ddec642f1790370b0977f75e5c40e92581ff632de012f960120135` |
| 已发布 Web 镜像 | `sha256:5b22cd0be64274937c15d51174a25b0063de8af272d848c0c80c3460952648f4` |
| 已发布 Backend 容器 | `39f5e0e8e8fb90ab6ab6ded373e5aa0fd533f577acd709b5739102fc24f2d0fa` |
| 已发布 Web 容器 | `004acda71885655cb5be011cff7a80e7bbabfee5ccba1bdb702acc191a903633` |
| 服务器私有发布目录 | `/opt/offersteady-global/releases/20261017-global-resume-optimizer-1` |
| 发布控制器 SHA-256 | `660c0938a384d3e8cbadf8276c3d89abeb2e69cad7096249bc3f7dfb116aeada` |
| 实际镜像探针 SHA-256 | `7180fa207922a8ea1abca02a0073f1fb0e594d5099fd8293585f8c0a6ac29a0e` |
| 最终上传包 SHA-256 | `9b83b503097b91f5360b78d927c5acd752e4721d812943676e15f73c0842dbbd` |

以各目标组件实际运行镜像派生候选，未用混合 Git 或 `current` 源整包覆盖。18 个批准 Backend 输入将包含迁移/依赖元数据的源清单从 290 项增至 302 项；其余源和旧功能依基线保护。完整路由从 215 条原路径增至 222 条（7 条新路径、9 个操作），原路径 schema/component schema 保留，既有 74 个 Prompt、鉴权/状态读取及问题预取优化保持。

Web 只取 proof 绑定的最终 64 个构建文件叠加实际旧镜像；排除本地历史目录残留的 30 个中间文件，保留原静态路径及不可覆盖的旧 hash 资源。最终运行静态清单为 217 项，符合 200 个旧路径与 64 个批准覆盖/新增输入的合并结果。后端仅显式新增启用 `OFFERSTEADY_GLOBAL_RESUME_OPTIMIZER_ENABLED=true`，原有效配置、环境、HostConfig、挂载、模型/供应商参数及 Web Nginx 配置保持。私有 Compose/Env、完整配置和凭据只留服务器；固定回退镜像及冻结上下文保留。

## 实际准备、门禁与切换

prepare（历史证据：`artifacts/global-resume-optimizer-20261017/production-prepare.json`）已构建固定候选，阶段结果 `productionChanged:false`；preflight（历史证据：`artifacts/global-resume-optimizer-20261017/production-preflight.json`）通过后，deploy（历史证据：`artifacts/global-resume-optimizer-20261017/production-deploy.json`）完成发布。打包证据中的 `productionMutated:false` 同样仅描述打包阶段，最终发布状态以 deploy/verify 为准。

控制器在预检及切换前重复执行六道只读门禁，使用固定旧 Backend 镜像、冻结环境和原网络的独立容器，覆盖普通/模拟/笔试、网页/桌面租约、音轨、回答/截图、资料处理及新简历任务，活跃/未知/读取失败均拒绝切换。本次实际预检及切换门禁通过；未结束面试、清理活动或放宽门禁制造空闲。迁移 `0053_global_resume_optimizer.sql` 通过现有 checksum/事务锁机制执行，仅新增本功能表，不执行破坏性 down migration或批量处理用户简历。

Backend 与 Web 分别按固定镜像发布，五个非目标 Global 容器及共享 Backend 标签保持。控制器具备进程互斥、完整双上下文/环境冻结、归属核对、断流后精确认领和受保护恢复；source/schema/context/tag/归属漂移停止自动切换，不覆盖后续变化。本次未触发生产回退；恢复分支的验证为本地合成测试，不能称为生产故障演练。脚本见[发布控制器](../../scripts/release_global_resume_optimizer.py)。

## 实际候选镜像及线上验收

实际候选镜像探针（历史证据：`artifacts/global-resume-optimizer-20261017/production-candidate-probe.json`）在无网络、只读文件系统、cap-drop/no-new-privileges 边界通过：完整 302 文件与 222 路径、既有 API schema、ReportLab 4.4.9/附带字体和真实 DOCX/PDF 均合格。network、database、fileWrites、threadStarts、subprocesses、dependenciesResolved、lifespan 七计数全零，未进入业务生命周期。此探针使用最终 `7180fa…` 版本；本地 rehearsal 的 `5f308e…` 为保留的历史版本，不能混作实际镜像证据。

独立 verify（历史证据：`artifacts/global-resume-optimizer-20261017/production-verify.json`）重新核对固定发布身份、完整 Backend/Web 文件、222 路径/完整 OpenAPI、环境/配置、Nginx、共享标签和非目标身份，通过后再次公开检查：

| 生产检查 | 实际结果及含义 |
| --- | --- |
| `/healthz` | 200，服务状态 `ok` |
| `/login` | 200 |
| `/offersteady-global-build.json` | 200，实际构建标识可读 |
| `/app/resume-optimizer` | 200，SPA 入口可达；不代表会员账号生成流程已在生产执行 |
| 未登录请求优化 capabilities | 401，`Cache-Control: private, no-store` |
| 未登录请求合成无效 job 的 PDF export | 401，`Cache-Control: private, no-store`，无文件内容 |

**本次生产鉴权检查只验证未登录拒绝。** 带授权的任务、会员日次数、编辑、删除、另存及真实文件响应是在本地真实 FastAPI/Service/隔离 PG 上验证；未创建生产测试会员、未使用真实用户资料或调用生产模型生成简历。

截至 **2026-10-18 00:03:43.289（Asia/Shanghai）**，短时观察（历史证据：`artifacts/global-resume-optimizer-20261017/production-short-observation.json`）通过：

| 组件 | 自启动观察 | 状态 | Restart | ERROR | Traceback | HTTP 5xx |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Backend | 263.23 秒 | running / healthy | 0 | 0 | 0 | 0 |
| Web | 227.65 秒 | running（未配置独立容器 health） | 0 | 0 | 0 | 0 |

`nonTargetsUnchanged=true`，仅保存脱敏聚合，未导出原始日志。短时零错误不能代替真实流量稳定性、模型质量或长期 P95 结论。

## 本地结果与交接边界

冻结发布包的 Backend 检查为 **353 项通过（127 新主套 + 215 适用既有回归 + 11 格式）**；随后同生产源码另补 1 项执行器隔离回归通过。新 Backend 为 127+1=128 个不同检查、Backend/格式共 354 个不同检查，均为分批结果，不宣称全集重跑。两个 CN 私有 helper 假设在实际旧 Global 源同样失败，原失败证据保留、最终适用集明确排除，不称为全仓全绿。

Global Web **223 项通过、0 skipped**，类型检查/英文审计/构建通过。Chrome 共 26 原流程 + 6 导出/另存错误增量 + 4 表格增量累计 36 场景；最终构建直接跑最后 4 项，前序构建以精确差异绑定，不宣称 36 全部跑最终版。真实本地 HTTP wire 25 响应、provider 0；真实 DOCX/PDF 的 1/3 页共 8 页渲染目视、Unicode/文本提取通过。发布保护合成测试 198 项通过。详细命令及限制保留在本地验收记录与逐场景表。

任务 28/28 的开发、自测和国际服发布记录已完成；未归档或提交推送。入口及会员规则已交接；真实模型效果、本人会员账号生成/下载体验由用户后续验收。未执行真实模型质量/抗注入成功率、实体设备、生产压力或长期 P95 检查。国服更新等待国际服用户验证后的另行授权。
