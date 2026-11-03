# 国服设备状态优化发布 cn-device-status-20261103.1

状态：**2026-11-03 02:14:21（北京时间）完成国服 Backend 发布，独立 verify 通过。** 切换前重复通过全部用户工作门禁，没有结束面试、清理活动或放宽保护。未提交或推送 Git。

用户明确授权发布[昨日完成的本地优化](cn-device-status-local-20261102.1.md)。仅更新 CN Backend 四份业务输入；Web、助手安装包 1.3.6、worker、国际服、模型/Prompt、收音、轮询频率、计费、数据库 schema/索引与运行依赖保持，连接池继续关闭。

## 本次改动与基线

CN 设备状态上报的同步绑定解析和发布改用既有控制执行器，避免阻塞事件循环；两次完整会话/资料读取改为既有五字段控制投影，仍分别保留权威 owner/存在与绑定状态、generation、心跳及会话状态检查。原错误、fallback、事件过滤与保存、并发结束语义保持。新增每20次采样一次的私有数值分段日志，区分排队、DB获取/执行/取数、绑定/事件仓库操作；无用户/会话/设备/请求标识、凭据、SQL参数、资料或异常文本。

发布前新鲜核对实际 Backend `sha256:c62df7ddbb92627de83c7c2733574c862678b120a11d051b346b9d13abfcf58a`、容器 `edd16865e5d5c0b1e57f33a696faf28cdffc340846db65e70150bb77a418a4dd`，完整运行232输入与 `release-20261102.1` 封存逐字一致。实际镜像内旧助手下载清单与运行可写层 d7 清单是唯一差异，已显式核对。Web366公开文件与封存完全一致，七个非目标组件的生命周期和配置签名固定。

候选从该实际固定镜像派生，只 COPY 四份已测业务文件和现有 d7 助手下载清单，不重新安装依赖或全量构建本地源码。候选233输入中229份非目标保持；根目录未发布的笔试配套未混入。镜像 Config 与原镜像全等，原层前缀保持。固定回退使用仅带当前1.3.6清单的 `sha256:15824dc57cdaaa817d171f11e3750cc84919750259a595c4741b042bbb2129ab`，完整232输入等于切换前实际运行字节，不使用会撤销热清单的裸 c62df 镜像。

## 验证与用户保护

本地最终候选497项回归通过，另补2项真实隔离PostgreSQL控制投影测试（计时28项重复回归一并通过），新增92项经独立重跑通过。58项其它专项用例未运行及相关验证限制保留在本地记录中。

此次发布控制器新增29项、探针14项及既有安全控制器65项，独立实际执行合计108项全部通过。覆盖单Backend范围、四业务SHA、热清单与回退、文件/配置漂移、七项工作门禁/TCP、busy/unknown/read failure、重复发布不重启、外来归属拒绝和已知失败的受限恢复。

实际候选镜像在服务器 network-none/read-only/cap-drop 环境通过探针，prepare再次复跑结果逐值一致：233输入、157份有效Python编译、Python3.13.15、44依赖和344项有效Settings保持，池false；完整203条API Schema保持 `dd7da7440bf0177b590396cf09253219eac1b6bf786e98f9fd0ce4bcf8eee272`。11组合成状态场景、2组慢仓库期间主循环响应及日志隐私检查通过，实际3个合成/控制线程全部释放。未进入应用lifespan，数据库操作、网络请求、文件写入和真实模型调用均0，生产私有环境仅留服务器。

初次观察、preflight及最终切换前均通过原七项只读用户工作门禁和当前Backend TCP8000门禁：真实普通/笔试/模拟面试、准备页、页面租约、音轨/发布者、未完成回答、资料/简历任务和有效账务均为空，无unknown/read failure。7个历史失败任务及22个历史孤立回答预占仅为原有信息项，没有清理或作为新例外；财务下界继续固定1792600214792，与当前原进程Id/StartedAt的orphanAnswerContext分开。

发布只切换 Backend 固定镜像，私有Compose/env/rendered输入和配置均冻结校验。七个非目标容器（包含Web/admin/worker）没有重建；若既有代理需要刷新，仅允许原安全流程 reload 而不改配置。已部署重入只verify，不重复重启；未知、漂移或读取失败停止，已知health/Compose失败恢复仍须证明归属并重复所有用户保护门禁。本次切换和验收通过，无需回退；故障恢复场景仅以合成测试验证，不冒充生产回退演练。

## 实际运行结果

| 项目 | 实际值 |
| --- | --- |
| Backend固定镜像 | `sha256:5efba4abea9b12e1af2b9d2c6e8f6edb2c205afed93f4f9fc9ba862e96499229` |
| Backend容器 | `035642d58f7eb9ad16f46a830d153130b1d2d6e7851401b0ec620cdaeed101bf` |
| StartedAt / 健康 | `2026-11-02T18:14:00.285020503Z`；healthy，RestartCount 0 |
| 运行输入 / API | 233份；完整203条Schema等价 |
| 配置 / 依赖 | 344项Settings逐值等价，池false；Python3.13.15与44依赖不变 |
| 当前助手清单 | `d7b106a6497bce873d67c2c81b045fab520aaa7382296978a8f6a04056e10927`；1.3.6保持 |
| Web / 非目标 | 366公开文件逐字不变；七个非目标组件签名保持 |
| 发布控制器SHA-256 | `19f3dab26b92185356600047c45b171705cc6c7d70f8b03b38c7dca6620be29d` |

独立verify核对真实镜像/完整输入/有效配置/Schema/依赖/七非目标及公网16项旧页面字节和health200通过。包含登录、普通面试、模拟面试、笔试、简历及SEO公开入口，页面与原Web完全一致。这些检查不代替用户登录后的完整业务和实体音频验收，也不把页面200当成实际面试端到端成功。

上线后约128秒的短时脱敏观察：Backend278行日志的ERROR/CRITICAL、Traceback、HTTP5xx和stream_failed均0；Web166行记录中有7次502。进一步逐时间脱敏核对，这7次均为实时控制类请求，集中在新Backend启动后的0.715–2.715秒，属于切换启动窗口；截至北京时间02:17:28，最近60秒没有新的5xx，Backend healthy且RestartCount0。不将本次窗口描述为“全部零错误”。见[错误观察](cn-device-status-20261103.1/post-release-error-summary.json)及[代理错误时段核对](cn-device-status-20261103.1/proxy-error-window.json)。

没有导出原始用户日志或资料，没有创建真实面试、付款、模型请求或进行生产压测。本地资料读取归零仅证明该路径减负，实际高峰P95改善仍需正常流量观察，不能承诺本轮消除所有数据库/检索/调度瓶颈。

[生产验收与切换门禁](cn-device-status-20261103.1/production-verification.json)、[完整运行输入](cn-device-status-20261103.1/backend-runtime-manifest.json)、[实际镜像探针](cn-device-status-20261103.1/candidate-probe-result.json)、[独立发布审查](cn-device-status-20261103.1/independent-release-review.json)、[上线结果复核](cn-device-status-20261103.1/post-deploy-review.json)。

完整脱敏本地证据目录为 `artifacts/cn-device-status-20261103-release/`；服务器私有发布目录为 `/opt/offersteady/releases/20261103-cn-device-status-1`。未来重建必须以当前实际镜像与冻结配置为基线，不能从旧目录直接执行Compose覆盖本次增量或现有助手清单。需求与发布约束见[生产追加规范](../../openspec/changes/lighten-cn-device-status-processing/specs/cn-device-status-production-release/spec.md)。
