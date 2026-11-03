# 国服实时共享阻塞优化：本地候选 2026-11-03

> 后续状态：本候选已于2026-11-04授权发布国服，[实际生产验收](cn-realtime-shared-20261104.1.md)已保留。以下为本地开发阶段的历史记录。

状态：**本地开发、自测和独立审查完成，未部署。** 用户要求先本地验证，晚上另行安排。没有 SSH、生产操作、真实模型调用、真实用户数据、Git 提交或推送。

本轮处理国服 Backend 的共享调度阻塞和内部重复读写。网页、助手1.3.6、模型与Prompt、计费规则、音频协议、轮询频率、国际服及worker保持；连接池仍关闭。API请求次数没有降低，减少的是一次请求内部的数据库和Redis工作，以及慢操作对其它请求的拖累。

## 实现内容

1. **隔离实时同步I/O和慢关闭。** CN publisher创建、音频连接/引导/帧准备、断开，以及会关闭ASR的暂停、恢复、结束和替换入口，交给独立有界执行资源。ingress为4个worker加16个排队槽，lifecycle为2加8；不占用原短控制执行资源。逐连接按原顺序等待，不并行重排帧。
2. **补齐取消和控制竞争的收尾。** 工作提交后不重放，槽位等实际worker结束才释放；调用者取消但创建成功的资源补偿清理一次。暂停/恢复/结束使用原会话清理锁串行，在执行时读取当前状态，结束后的迟到恢复不能复活会话。保留权限、模式、计费和原错误合同。
3. **消除CN全局状态快照写放大。** 候选、账号设备关联及绑定改为实体原子写，网络I/O不再持有进程全局runtime锁。候选领取/绑定/释放增加可选CAS防止同毫秒并发覆盖；保留旧数据读取、退役防复活、历史关联和TTL规则。新CN绑定使用独立命名空间，旧v1值和索引字节保持。
4. **合并同次资料读取。** CN非mock单次会话刷新和检索metadata按文档去重，在仓库支持时使用一次批读；无批读实现沿逐唯一ID读取。没有跨请求缓存资料或权限，预取前后两次独立权威读取及末尾指纹校验保留。
5. **补充低频数值观测。** CN增加有界主循环延迟样本和1/20工作分段采样，区分入场/排队、worker执行及loop恢复。只记录固定标签和数值，不含用户资料、音频或标识；计时/日志失败不改变业务结果，不新增页面说明或HTTP路由。

## 实际来源与候选边界

起点为当前已记录的实际CN Backend镜像 `sha256:5efba4abea9b12e1af2b9d2c6e8f6edb2c205afed93f4f9fc9ba862e96499229`，来源见[当前国服基线](../current-cn-baseline.md)及[233输入清单](cn-device-status-20261103.1/backend-runtime-manifest.json)。本轮没有重新访问服务器。

独立本地候选位于 `artifacts/cn-realtime-shared-local-20261103/candidate-final/`。按[组装脚本](../../scripts/build_cn_realtime_shared_candidate.py)的12文件允许列表叠加，233份已捕获输入变为237份；225份非目标内容和文件权限一致。12份根目录增量与冻结候选SHA一致。仓库中尚未发布的笔试 `screenshot_answer.py` 配套明确排除，不能用根目录全量构建替代本候选。

这233份是此前捕获的Backend核验输入，**不是完整镜像所有层的文件清单**。本次合成上传回归通过test-only路径解析读取未改的本地 `material-upload-formats.json`，它由Dockerfile单独复制，未包含在233份中；没有修改冻结候选或声称本轮已核验生产该辅助文件。将来构造实际候选镜像时仍须核验它及原镜像保留内容。

相同合成配置下，基线与候选的完整 **203条OpenAPI定义相同，344项Settings逐值指纹相同**，有效Python编译 **161份通过**；依赖、Prompt及助手d7下载清单均在未改输入中。Schema探针未启动lifespan、线程或网络。这是本地源与配置等价验证，未执行生产私有配置或实际候选镜像探针。

## 已执行的验证

最终冻结候选统一回归：**956通过、1跳过、0失败/错误**，64个测试模块及2个foundation用例，pytest用时33.24秒。唯一跳过是Global专属source lifecycle；另3个Global-only模块依赖实际CN基线中不存在的服务，未混入候选，不能将此轮称为国际服全量验证。共有5条已有依赖/测试环境警告，未隐藏。

覆盖鉴权、设备状态、心跳/状态读取、实时新旧协议、事件及资源清理、截图和多屏笔试、模拟面试权限/音频/截止/清理、预取与检索、账务和积分，以及新增慢I/O、容量、取消、竞争、TTL和迁移兼容场景。使用独占临时Redis7.4.9和两个合成PostgreSQL实例，不读产品.env，限制网络至自建本机测试服务；没有真实模型、付款或物理音频设备端到端测试。三个临时容器及本轮独立数据库已清理，既有本地服务未动。

独立审查重新核验237份候选SHA，并执行81项相关回归全部通过，特别复核关闭时排队取消与迟到资源补偿、原子退役和旧v1字节兼容。专项还分别验证了真实合成PG的单statement快照/事务释放、Redis7.4兼容及多实例CAS。专项与完整回归有重叠，**不把通过数相加**。

初次验证发现测试环境缺少已存在的可选`psycopg_pool==3.3.3`，只安装到忽略的本地测试目录，未改项目或共享环境依赖，也未开启产品连接池。旧Mock会虚构新增可选方法，已用明确spec对齐原单读仓库；未减少原读次数和权限断言。直接调用未绑定方法的旧Mock测试显式绑定真实控制body，并补充CN/Global真实实例四例。foundation一项原断言在关闭后读取已清理状态，实际旧基线也失败；将原活动断言移至连接内，补充关闭后清理断言。上述原失败、修复证明和最终结果均保留，没有因失败改变本轮产品范围。

## 合成对照与实际含义

| 同一合成场景 | 旧基线 | 本地候选 | 说明 |
| --- | ---: | ---: | --- |
| 150ms慢关闭时，无关timer额外等待 | 153.633ms | 0.267ms | 关闭自身仍约158ms，调用次数均1；验证隔离效果 |
| 3份资料、6个同文档片段的预取连接获取 | 18次 | 9次 | 同次权威资料批读，前后检查保留 |
| 2份资料、无知识库场景连接获取 | 7次 | 5次 | 单次合成操作计数 |
| 100个候选、20次保存的直接Redis命令 | 120条 | 20条 | 热路径实体写 |
| 上述Redis全局快照写（含warmup） | 21次 | 0次 | 去除全局快照重写 |

Redis直接命令参数字节3,733,105→55,060，本机保存P95为0.872→0.207ms；字节不含RESP、回复及嵌套pipeline细节。这些是局部机制/工作量对照，**不能换算整体线上P95，不能承诺8秒降到某个值，也不能据此给历史峰做精确原因占比**。

## 剩余限制与晚间交接

- 没有治理全部其它async只读/确认入口、供应商延迟或全部数据库瓶颈；后续依靠新增数值分段观察真实正常流量。
- 已运行的Python外部I/O线程不能被硬杀；关闭依赖正常ASGI先关闭连接/任务再退出lifespan的顺序。
- 兼容支持新代码读取旧状态，**不支持旧/新binary同时写**。旧binary无法看见只在新实体中发生的活跃变更，后续发布和回退均须空闲、单writer门禁，不允许活跃面试中混跑或回退。
- 用户晚间另行指示后，才重新读取实际镜像/配置并构造固定镜像，核验功能路由、辅助输入与原优化，准备明确回退，等待全部用户工作空闲后切换。此次本地通过不授权自动上线。

本轮分支 `codex/cn-realtime-shared-blocking-20261103`，没有提交或推送。生产事实仍以[当前国服基线](../current-cn-baseline.md)为准。

验证入口与材料：

- [OpenSpec需求](../../openspec/changes/isolate-cn-realtime-shared-blocking/proposal.md)、[方案](../../openspec/changes/isolate-cn-realtime-shared-blocking/design.md)、[任务](../../openspec/changes/isolate-cn-realtime-shared-blocking/tasks.md)
- [脱敏最终汇总](cn-realtime-shared-local-20261103.1/verification.json)、[12文件与SHA](cn-realtime-shared-local-20261103.1/delta-manifest.json)、[独立审查](cn-realtime-shared-local-20261103.1/independent-review.json)
- [能力场景核对](cn-realtime-shared-local-20261103.1/scenario-verification.json)、[本地资源清理](cn-realtime-shared-local-20261103.1/cleanup.json)
- 完整选择、测试runner、import/network guard、JUnit、原失败及合成对照位于 `artifacts/cn-realtime-shared-local-20261103/`。完整suite重放需要重新创建独占合成实例，不能复用已清理的lease，也不能指向现存用户库。

无需数据库即可重放Schema/编译探针及strict校验（Python使用项目已有虚拟环境）：

```bash
env -i PATH="$PATH" OFFERSTEADY_ENVIRONMENT=test /Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python -B artifacts/cn-realtime-shared-local-20261103/inspect_schema.py artifacts/cn-realtime-shared-local-20261103/candidate-final
npx openspec validate isolate-cn-realtime-shared-blocking --strict
```
