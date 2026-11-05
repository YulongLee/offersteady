# 国服单用户测试 API P95 诊断（2026-11-04）

只读观察截至北京时间2026-11-04 03:58:51。线上Backend镜像dc8、容器7849健康且未重启；四份相关实际运行源码SHA与已发布固定候选一致。没有修改生产代码、配置或用户状态，没有重启、部署、调用真实模型或生产压测。

## 主要发现

已确认本轮新增CN实体分支引入固定绑定查询的性能回退。助手的active-connection请求带pinnedSessionId/pinnedBindingId时，先列出全站绑定，再按设备过滤；列出过程对每条绑定逐个查Redis退休状态。实际全站绑定1191条，每次该列表调用由代码关系推导为1次HVALS+1191次HEXISTS。发布前snapshotReload=false的相应方法在进程内筛选，没有这些往返。

本地真实候选方法配合合成Redis计数复现：全站1/10/100/1000条、目标设备始终1条时，分别2/11/101/1001次往返。该结果为操作数验证，不是生产逐段计时。当前源码证据：

- [pinned入口](cn-api-p95-20261104-current-test/f99ed164-realtime_speech_service.py) 2585–2595。
- [全站后过滤](cn-api-p95-20261104-current-test/95ee4fdc-redis_realtime_speech_repository.py) 586–589。
- [逐条退休检查](cn-api-p95-20261104-current-test/1fc7fc7b-cn_realtime_entity_state.py) 394–402。
- [发布前对应基线](cn-api-p95-20261104-current-test/4ee95269-redis_realtime_speech_repository.py) 497。

## 线上聚合

测试窗口2026-11-04 03:48:00至2026-11-04 03:58:51：

| 口径 | 请求数 | P95 ms | 最大 ms | ≥1秒 |
| --- | ---: | ---: | ---: | ---: |
| 普通HTTP合计 | 1662 | 1265.02 | 3539.69 | 112 |
| active-connection | 583 | 1772.6 | 3539.69 | 112 |
| 排除该路由后的重算 | 1079 | 117.26 | 670.03 | 0 |

这次测试窗口全部112次≥1秒请求均来自active-connection。最近五分钟出现12个不同设备路径，6个有秒级慢请求，其余6个最大值低于93ms；这不代表12位面试用户，也不证明设备归属。代理参数形状另确认170次带双pinned参数、107次不带，277次均200。没有逐请求参数与耗时join，不能声称每一条慢请求均已追踪到具体pin状态。

同窗口主循环摘要p95约2ms、最大136ms，健康请求最大2.36ms，音频ingress work采样最大10.492ms；控制线程未报告饱和。数据库只读快照无blocked/idle-in-transaction/deadlock，单次连接23.259ms；这些是当前证据，不是历史整段数据库等待的排除证明。

后台API P95是进程最近5分钟普通HTTP请求综合分位，每30秒采点，不等同当前一位用户或完整回答生成耗时。排除admin后的P95仍高，当前主要拉高者为助手连接状态接口。排除该接口重算的117.26ms仅用于定位，不能当作修复后降幅。

## 建议修复与边界

按已固定session/binding直接读取并验证设备、机器码、bindingId/generation、退休fence和数据库权威状态，避免全站HVALS与逐条HEXISTS。保留绑定/权限/结束面试检查，不以延长缓存或从指标删除慢路由替代修复；可仅改后端，助手1.3.6协议可保持。

这是本轮漏测的实际历史数据规模路径；既有隔离回归通过不等于无性能回退。本次只诊断，尚未实施修复。此观察不能证明全部用户体验或所有功能正常。

脱敏证据：[诊断摘要](cn-api-p95-20261104-current-test/0cc8270e-diagnosis-summary.json)、[路由与分段](cn-api-p95-20261104-current-test/466a9294-current-log-aggregate-r2.json)、[绑定规模与轮询设备](cn-api-p95-20261104-current-test/2f0ea770-poll-shape.json)、[实际源码](cn-api-p95-20261104-current-test/fe2df409-source-verification.json)。原始日志、用户/会话/设备标识与私有配置未导出。
