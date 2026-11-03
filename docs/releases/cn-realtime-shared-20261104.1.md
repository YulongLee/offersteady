# 国服实时共享阻塞优化发布 cn-realtime-shared-20261104.1

状态：**2026-11-04 03:33:48（北京时间）完成国服Backend发布，独立verify及短时观察完成。** 用户已于2026-11-04授权将[本地已测优化](cn-realtime-shared-local-20261103.1.md)部署国服。实际切换和验收结果以下方记录为准。

## 范围与实际基线

仅CN Backend十二份业务增量：实时同步I/O与慢关闭隔离、同会话暂停/恢复/结束串行及取消收尾、Redis实体原子状态保存、同次资料批读去重和有界数值观测。Web、助手1.3.6、Global、worker、模型/Prompt、收费、轮询、数据库schema/索引及44依赖保持，连接池仍关闭。没有Git提交或推送，也没有执行此前另查账号的积分返还。

部署前新鲜只读核对实际Backend为 `sha256:5efba4abea9b12e1af2b9d2c6e8f6edb2c205afed93f4f9fc9ba862e96499229`、容器 `035642d58f7eb9ad16f46a830d153130b1d2d6e7851401b0ec620cdaeed101bf`，StartedAt为 `2026-11-02T18:14:00.285020503Z`，healthy且RestartCount0。运行可写层与固定镜像的233份已捕获输入完全一致，均带现行助手d7清单；另核验单独复制的 `material-upload-formats.json`，运行及镜像SHA均为 `e6607164d21950319ab2b6179d38ed6cf771715a2663c18db704af612907ac2f`。

完整203条Schema、344项有效私有Settings、Python3.13.15/44依赖、366份Web公开文件及七个非目标签名已冻结；私有配置、环境和Compose快照仅留服务器。根目录未发布的笔试配套未混入。

从实际5ef固定镜像只COPY已测十二文件，候选为 `sha256:dc8f3bb3aa95b6615686226c95612d7b3973860d2b2da0dd391a316134266b9b`；Config全等、原基础层前缀保持，237份候选输入中225份非目标保持。固定回退为原5ef镜像，不重新安装依赖或全量构建根目录。

## 已执行的验证与保护

本地产品回归为956通过、1项Global专属跳过。实际候选镜像以network-none、read-only、cap-drop和服务器本地私有环境执行探针，并通过237输入/161份有效Python编译、203完整Schema、344有效Settings、44依赖、池false、辅助上传格式和d7清单核验；包含11组设备状态、慢关闭隔离、顺序/取消补偿、资料批读、Global及普通/笔试/mock守卫等合成场景。9个合成工作线程全部释放，未进入lifespan，DB/网络/写文件/真实模型操作均0。

r3最终发布回归153项通过，另236个子用例通过；与专项测试重叠，不另加总。覆盖控制器来源与配置漂移、prepare/preflight/final及回退重复门禁、已部署仅verify、新旧writer不混跑、实际启动命令和进程数证明、辅助文件及非目标保持、未知与读取失败停止。

保留原七项只读用户工作门禁、原TCP8000检查和财务下界1792600214792，新增只读CN实体门禁，覆盖新namespace绑定/候选/CAS claim、退役/owner/activity和可见并发修改；不构造会seed的业务仓库、不续TTL或清状态。任何切换或恢复均须重新核对空闲、归属和单writer；旧binary无法读取仅新entity中的活跃变更，不允许活跃面试期间回退。

初次准备在任何服务切换前被 `single_writer_command_unproven` 安全拒绝。原因是新检查器只识别直接uvicorn，而实际原镜像使用Dockerfile中的 `python -m uvicorn`。仅修正命令识别并补实际Dockerfile/绝对路径、拆分Entrypoint、非法wrapper/多worker/进程计数等回归，业务代码未改。原 `...-1` 目录和校验输入不覆盖；新 `...-2` 目录重新观察，基线与第一次逐字段一致，再复跑实际镜像探针。

此前r2目录 `/opt/offersteady/releases/20261104-cn-realtime-shared-2` 及其d63d2588…控制器保持原样。用户退出后仍有1条持续连接，前述严格TCP0检查一直正常等待，未执行切换。

用户随后明确指示“你不用管部署上线吧。我线上没有进行中的面试”。因此新增仅限精确原Backend、尚未切换且非recovery的TCP0或1例外；必须同轮原七项和CN实体保护工作全部通过，并保留原TCP的进程/namespace/格式/新鲜度校验及唯一writer/冻结来源证明。TCP大于1、任何活跃工作、unknown/read failure仍阻止切换；新候选及所有恢复/回退仍严格TCP0。没有单独杀连接、清理状态或跳过八项工作门禁。

新服务器发布目录为 `/opt/offersteady/releases/20261104-cn-realtime-shared-3`，控制器SHA为 `3559e8924a773929517583baea1ffeb43c32017795989edc48526f96c5a07dee`；旧目录/控制器不覆盖。r3重新观察的基线/配置/非目标与r2逐字段一致，实际镜像探针再次通过，prepare已成功；preflight、deploy和独立verify均已成功，真实切换结果见下。原自动等待任务已删除，不会再按旧r2约束重放。

## 验收结果

| 项目 | 实际结果 |
| --- | --- |
| 固定Backend镜像 | `sha256:dc8f3bb3aa95b6615686226c95612d7b3973860d2b2da0dd391a316134266b9b` |
| 实际容器 | `7849b16dc46c45c97e70b62d40391a7458c1819f37bdad58f873159936571e8d` |
| StartedAt | `2026-11-03T19:33:26.429918438Z` |
| 健康 / 重启 | healthy；RestartCount0，03:37:53短窗口结束复查仍保持 |
| 实际输入 / 非目标 | 237份；225份原输入保持，12变化中4新增 |
| API / 有效配置 / 依赖 | 完整203 Schema保持；344 Settings保持；Python3.13.15与44依赖保持；池false |
| Web / 非目标组件 | 366份Web公开文件、七个非目标签名保持 |
| 助手 / 辅助文件 | 1.3.6现行d7清单及独立上传格式文件SHA保持 |
| 原公开页面检查 | 16项字节核验通过，health200；不代表用户登录后真实面试端到端测试 |
| 回退 | 固定原5ef镜像；任何恢复仍重复八项工作及严格TCP0/单writer门禁 |

实际切换前八项用户工作门禁均通过：普通/笔试/模拟、准备页/租约、音轨/发布者、回答/截图、资料/简历与有效账务均无保护活动，unknown/read failure为0。旧7份失败任务和22份历史孤立预占仍按原信息口径保留，没有清理。TCP8000为1，按用户追加授权仅对原精确Id/image采用例外；服务器原字节gate文件SHA与授权proof一致，progress与deployed归属均为新镜像/新容器。没有单独杀连接或结束面试，只有正常Backend更新引起残留连接短暂重连。没有回退或第二次重启。

新Backend启动后约178.59秒的脱敏观察：Backend636行的ERROR/CRITICAL、Traceback、HTTP5xx、stream_failed和补偿清理警告均0。Web359行有**17次502**，不能描述为全部零错误。进一步截至03:37:53逐时间只读聚合：17次均为实时控制类请求，集中于新Backend启动后0.571–3.571秒（03:33:27–03:33:30），均早于03:33:48发布验收完成；其后及最近60秒无新增5xx。健康与RestartCount0在窗口结束再次核对通过。

新增主循环监测产出5次数值摘要，容量上限512，最新摘要p95约2.029ms、max131.529ms；早期含一次1351.787ms调度漂移。**这些是安静时段主循环调度样本，不是API P95，也不是高峰改善证明。** 同窗口未采到共享I/O分段样本，不能据此补造实际流量工作相位。161份Python编译来源于同固定镜像实际候选探针，collector未独立重新编译。

验收材料：[实际生产核对](cn-realtime-shared-20261104.1/production-verification.json)、[237输入](cn-realtime-shared-20261104.1/backend-runtime-manifest.json)、[实际候选探针](cn-realtime-shared-20261104.1/candidate-probe-result.json)、[控制器独立审查](cn-realtime-shared-20261104.1/independent-controller-review-r3.json)、[生产证据独立复核](cn-realtime-shared-20261104.1/independent-post-deploy-review.json)、[短时错误统计](cn-realtime-shared-20261104.1/post-release-error-summary.json)、[切换proof与502时段](cn-realtime-shared-20261104.1/cutover-proof-and-proxy-window.json)。

没有真实用户内容、原始日志、地址或令牌导出；没有创建真实面试、付款、模型请求或进行生产压测。模型/收费/助手/Web/Global/worker/连接池及数据库结构保持；没有Git提交/推送。当前已可交用户测试，实际高峰API P95改善仍需正常流量下的同负载对照，不能承诺8秒固定降到某个值。

全部脱敏证据位于 `artifacts/cn-realtime-shared-20261104-release/`。生产要求见[追加规范](../../openspec/changes/isolate-cn-realtime-shared-blocking/specs/cn-realtime-shared-production-release/spec.md)及[发布任务](../../openspec/changes/isolate-cn-realtime-shared-blocking/tasks.md)。
