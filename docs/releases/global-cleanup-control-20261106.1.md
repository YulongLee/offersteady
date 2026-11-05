# 国际服读取与连接关闭隔离发布 global-cleanup-control-20261106.1

2026-11-06 03:00:39（北京时间）完成，仅更新Global Backend。独立verify、实际来源/配置/Schema验收及公开入口检查通过。用户授权国际服部署后再上传Git并封版；国服保持01:22发布后正在观察的版本。

## 来源与范围

从实际运行457a镜像/efec容器的307份输入开始，六改一增为308份，301份原输入逐字保持。实际新镜像`sha256:687fe1b4b421eb11024bbe6fd36f8ff81a973cf37a74f43e653e7e9321752bea`，容器`bf9eab2626100d1b090de78e3cab6f6fa00a727d6181c54c61ccb3e4f70eb197`，StartedAt`2026-11-05T19:00:16.221773511Z`，healthy、RestartCount0。仅在原镜像COPY七份审核输入，基础层/Config保持，无根目录整包构建。

同步内容：按用户索引读取绑定/设备；结束单场按会话定点读取；准备通道独立2+8；支持可选接口的QwenRealtime连接先逻辑解绑，再在有界2+8通道关闭捕获的旧连接；性能ACK使用权威轻读，跳过未启用DEBUG的序列化。Task及旧gateway保持原关闭接口，不能声称所有协议都进入新关闭池。队列满时内联关闭、submit含糊失败只执行一次、停机排空，并保留Global关闭失败计数。

Global原有计费/时间会员/Creem、模型/Prompt、语言、1.5秒状态缓存、结束事务/事件、鉴权/退役和取消保护保持。只有必要fence提前至物理关闭前；未替换国服整文件。Web251、worker267、正式助手1.3.6及历史下载、七个非目标保持，国服238/196/366来源也已新鲜只读验证保持。

## 测试与发布保护

本轮Global合成回归497项通过（175共享/规模、208业务、114扩展），包含真实独占Redis的1/1242/10000历史及TTL/迁移/精度/损坏/并发，命中两种owner列表共2次传输/2条解码，服务端全站扫描0。真实独占PostgreSQL覆盖状态、资料和模拟面试；既有历史对照测试因CN完整读取此前已改为批读，已改为核对Global当前真实SQL预算，不沿用过时的6次逐资料读取预期。全部497项无跳过；发布控制器50项、复用生命周期及实体门禁144项通过。

实际固定候选镜像在network-none/read-only/cap-drop下验证308输入/172编译、223完整Schema/379有效配置、Python3.13.16/46依赖、辅助格式/助手、旧功能和新关闭/准备/ACK行为，13个合成线程全部释放。镜像探针不连接数据库/模型或进入lifespan；真实Lua/SQL在本地独占合成服务验证。两个自建合成容器已按租约核对后移除，未触碰其他实例。

冻结目录`/opt/offersteady-global/releases/20261106-global-cleanup-control-1`；控制器SHA`40c566cd79ffcf28e5250ff6d0eb9d0f9dd10244742d9ac662e02923ea50d63f`。prepare/preflight和切换重复七项工作门禁、实体、TCP0和单writer/归属检查，未中断任何用户工作或使用残余连接例外。恢复同等门禁；固定回退为原457a，未执行回退或重复重启。私有Compose/配置/环境留服务器。

## 观察与限制

首轮108.48秒观察中Backend与Web均无ERROR/CRITICAL、Traceback或HTTP5xx；验收后亦无流失败/清理警告。仅有3条验收内普通API样本，不能给出生产用户P95改善承诺。启动时完整Schema核验最大1892.92ms，主循环窗口保留1671.246ms最大漂移，包含首次Schema生成；不是稳定面试流量测试，也未隐藏该启动长尾。没有调用真实模型、创建面试/付款或生产压测。

更长观察以封版[evidence](../../releases/20261106.1/evidence/post-release-error-summary.json)为准。建议用户测试开始/结束、暂停/恢复、重连、笔试和模拟面试，实际高峰效果继续随正常流量观察。

## 公开证据与封版

[实际验收](../../releases/20261106.1/evidence/production-verification.json)、[国服保持](../../releases/20261106.1/evidence/cn-preservation.json)、[镜像探针](../../releases/20261106.1/evidence/candidate-probe-result.json)、[回归](../../releases/20261106.1/evidence/regression-summary.json)、[规模操作数](../../releases/20261106.1/evidence/synthetic-scale-cost.json)、[匿名边界](../../releases/20261106.1/evidence/public-boundary.json)、[节点审查](../../releases/20261106.1/evidence/source-review.json)。实施任务见[OpenSpec](../../openspec/changes/sync-global-cleanup-control-20261106/tasks.md)，两服精确公开运行来源与恢复工具见[release-20261106.1](../../releases/20261106.1/README.md)。
