# 国服控制查询与连接复用：本地候选 20261028.2

> 后续用户授权的国服发布已于2026-10-29完成，连接池保持关闭，见[生产发布记录](cn-state-control-20261029.1.md)。下文保留10月28日本地交付时的状态与结果。

状态：**本地候选，未部署、未重启线上、未修改生产配置或用户数据，未提交/推送Git**。继续叠加[今天第一轮候选](cn-state-read-local-20261028.1.md)，由用户晚上另行安排更新。

## 本轮内容

1. CN伴随绑定检查只取会话ID、归属、状态、会话模式和音频模式，不再为简单状态查询刷新全部绑定资料或附带写回。正式回答、资料感知操作与捕获授权沿原完整校验。
2. authentication/session两个高频PostgreSQL仓库可共享一只有界连接池；默认关闭，仅CN Backend生命周期显式激活。Global、未激活Backend生命周期的worker、billing和document继续原连接路径。
3. 保留原事务提交/回滚、cursor行格式和逐次权威读取；不缓存身份/权益/资料，不自动重放业务SQL。启动失败、关闭、延迟归还、多应用引用、不同配置和fork均有保护。
4. 补充隔离本地实际仓库的建连、借用、SQL执行和整体操作对照。没有调整模型、Prompt、预取策略、心跳/轮询频率、收费或前端界面。

## 本地实测

证据目录为 `artifacts/cn-control-db-local-20261028/`，所有数据合成、数据库专用localhost容器（1 CPU / 512 MiB / 临时数据卷），不调用真实模型或供应商。

### 控制查询

相同六份资料、真实会话与资料PostgreSQL仓库，双方都绕过原pairing短缓存、连接池关闭。60次/组、并发1，每次绑定响应等价、两组均0错误：

| 指标 | 原完整会话读取 | 控制投影 |
| --- | --- | --- |
| 每次物理连接 / SELECT | 7 / 7 | 1 / 1 |
| 每次资料读取 / 会话写入 | 6 / 0 | 0 / 0 |
| 操作P50 | 36.399 ms | 5.196 ms |
| 操作P95 | 40.936 ms | 6.381 ms |

另一个绑定资料已缺失的单次场景，原路径9次连接、7次SELECT、2次写回，候选1次连接、1次SELECT、0写回；绑定响应仍等价。原业务路径的写回行为没有改变。该场景单独计数，未每轮人为重置以夸大收益。

### 实际鉴权与会话仓库连接复用

每组120次操作，每次执行一次真实鉴权状态SELECT和一次会话控制SELECT；并发分别1/4/8，六组均0错误、结果等价：

| 并发 | 原短连接操作P95 | 连接池操作P95 |
| --- | --- | --- |
| 1 | 12.619 ms | 3.068 ms |
| 4 | 37.241 ms | 6.264 ms |
| 8 | 100.724 ms | 11.156 ms |

每组业务SELECT均240次；短连接测量期间创建240个连接，池预热4个连接单列、测量期间新增0个。池每组另有240次空SQL健康检查往返，已单独统计，**不是额外240次SELECT 1**。借用计时包含等待、可能的建连和健康检查；execute计时不是纯服务端SQL CPU时间，不能相加不同分项的百分位。

以上为同机合成路径对照，**不能换算为线上整体API P95降幅**。生产各分项贡献、冷启动与合适池大小仍需真实候选和发布后数据核验。

## 自测与独立审查

- 相关后端集成回归471项通过、1项Global专属生命周期跳过。包括前轮状态复用、鉴权/撤销、控制状态、心跳、资料权限、普通/模拟面试、60分钟截止、简历和收费。旧简历测试硬编码的另一本地库已在本次测试进程中重定向到专用合成库，未修改原夹具或其它本地服务。
- 连接池专项39项通过，独立审查者在同一专用库另外复跑39项通过。覆盖默认关/Global/worker原路径、共享总上限、配置隔离、提交/回滚、SQL失败、坏连接、等待超时/队列、关闭唤醒、延迟归还、fork及真实FastAPI正常/启动失败生命周期。
- 另补正确进入真实应用lifespan的合成流式回答2项（池关/开）通过：真实PG鉴权、会话和ChatService，验证`task-started → quick-completed → completed`及任务保存；提交会话结束后新回答被拒绝且不新增任务/网关调用。此用例的回答仓库为内存、realtime为合成事件sink、计费和ASR未启用，不冒充完整收费/采集E2E。以上三组最终相关用例按标识去重为**512项通过、1项Global专属跳过**。
- 控制专项与相关既有回归104项通过（与上面回归有重叠，不重复累计）；基线状态/mode/audio、pinned、owner、软删除、generation/TTL、正式资料校验与wire等价覆盖。
- 新旧前端输入未变，沿用今天已执行的662项前端测试、类型检查与生产构建证据，未无意义重复执行。编译155份有效Backend Python源通过，既存AppleDouble `._` 元数据文件不作为Python源码编译。
- 初次新专项中的夹具缺少事件方法、非法音频模式和异步归还等待断言已纠正并复跑，初始失败记录保留；没有修改产品逻辑或放宽断言来掩盖问题。

### 扩大旧测试集发现的限制

扩大执行整个旧foundation集时发现9项失败，主动中断用于定位，结果保存在 `backend-expanded-interrupted.{txt,xml}`；不能把该次运行称为完整通过。

对失败的9项，用import hook分别加载扩展前冻结8个模块和当前候选，并保留原模块路径、相同环境与断言：**两版均8项失败、1项通过，失败消息完全一致**。实际网络被阻断，外网尝试为零。五项SSE测试的旧`TestClient`未进入lifespan；另三项为旧微信生产配置断言、mock远端网关契约及合成音频性能字段预期不一致。这里只证明它们在本轮前可复现，不推断真实生产安全/音频故障。

剩余预热350ms门槛在最初大组耗时约405ms，冻结基线和候选的隔离复跑都通过；仅能标注大组时间敏感失败未复现，**不能声称整套时延稳定已解决**。详细证据为 `foundation-nine-baseline-comparison.json`。本轮未改旧断言，未顺手扩大到相关供应商或预热策略修复。

此前网页的既存SEO/Nginx与包体预算检查限制继续见第一轮记录，本轮未放宽或修复这些检查。

## 源码保护与候选范围

- 扩展前保存157份输入，其中1份既存`._`元数据仅记录；156份有效输入快照哈希正确。本轮9份既有输入改变（8个Python模块及pyproject），147份不变；新增运行模块仅 `app/platform/cn_hot_database.py`。
- 精准AST对照确认8个目标Python模块非目标代码保持；前轮DocumentService、Web聚合及SessionService.list_sessions/get_session、心跳/捕获等14个核心方法保持。
- 557份前端、Global、桌面和AI受保护输入哈希全部不变。没有AI行为变更，无需新增Prompt评测。
- 前一轮候选仍在当前工作树；本次只新增后端增量。线上来源以[当前国服基线](../current-cn-baseline.md)及当天只读镜像证据为准，不能把完整工作树构建当作线上静态包等价。

## 配置和晚间发布边界

新配置见[环境变量说明](../environment-variables.md)。池开关默认`false`；实验初值max=4、max_waiting=16、timeout=3秒不是生产容量结论。轻量控制投影在CN生效，连接池可独立启用或关闭，是否随夜间发布开启必须在当次发布记录明确。

运行依赖固定`psycopg_pool==3.3.3`；本地仅在临时模块目录加载，主虚拟环境未修改。夜间应从当时实际Backend镜像制作候选，只加入确切源码和已校验的新依赖，核对运行时Python/psycopg兼容；不能因重装依赖顺带解析升级其它库。此前隔离wheel的SHA-256为`9b9cd6a4fcec47a410f7e82d408540e7f77b478509e91b44c1a5457a13e5ff37`，依赖凭据与生产私有配置留服务器。

晚间仍须重新核对实际镜像、前后端功能路由及私有配置；制作最小增量、验证候选实际依赖和应用生命周期，执行用户工作门禁、固定镜像和回退验收。此时没有部署授权，不停止用户、不重启或修改其它组件，不自动安排夜间更新。

## 可复核命令

所有数据库环境变量仅指向专用localhost合成库，不在文档记录DSN：

```bash
PYTHONPATH=apps/backend python -m pytest apps/backend/tests/test_cn_control_state_reads.py apps/backend/tests/test_realtime_control_plane.py apps/backend/tests/test_web_heartbeat_lightweight.py apps/backend/tests/test_cn_state_document_reuse.py -q
PYTHONPATH=apps/backend:<isolated-pool-module-dir> python -m pytest apps/backend/tests/test_cn_hot_database.py -q
PYTHONPATH=apps/backend:<isolated-pool-module-dir> python -m pytest apps/backend/tests/test_cn_live_answer_lifespan.py -q
PYTHONPATH=apps/backend:<isolated-pool-module-dir> python tools/state_read_optimization/hot_repository_comparison.py --samples 120 --output <local-report-path>
openspec validate lighten-cn-control-database-access --strict
openspec validate reduce-cn-state-read-overhead --strict
git diff --check
```

Python使用已存在的项目Python3.13.9虚拟环境。具体环境隔离、测试文件列表及JUnit见本地 `run-local-regressions.py`、`test-summary.json` 与对应输出；本轮没有真实模型、真实支付或操作系统收音测试，相关运行代码保持。
