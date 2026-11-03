> 后续更新：本地候选已于2026-11-04 04:25:57（北京时间）完成[国服发布](cn-pinned-binding-20261104.1.md)。以下为本地交付时的历史范围与验证，当前生产以发布记录为准。

# 国服固定绑定查询本地修复 cn-pinned-binding-local-20261104.1

本地交付时状态：**修复与自测完成，当时尚未部署。** 本轮开发不SSH、不重启或修改线上；不提交/推送Git。线上仍以[当前国服基线](../current-cn-baseline.md)的dc8实际组件为准，旧生产发布控制器不能重放。

## 问题与修复

[只读线上诊断](../diagnostics/cn-api-p95-20261104-current-test.md)发现，本轮CN实体化后的已固定绑定查询在按设备过滤前遍历全站1191条历史绑定，并逐条查Redis退休状态。测试期间全部112次≥1秒普通请求来自active-connection，最大3.54秒。这是已发布增量中的性能回退，原功能回归没有覆盖高频命中路径随历史规模增长的成本。

本补丁仅替换CN带完整pin的读取：沿既有session→owner索引，在单次只读Lua中读取canonical绑定和退休位；不遍历全站，不修改TTL/索引/seed/activity，不延长缓存。保留设备、机器码、session/binding/owner、generation、新鲜度、退休fence及数据库权威状态检查。正常pin缺失/失效沿原latest回退；内部身份或JSON损坏按原错误合同拒绝，不能伪装正常未命中。Global/旧仓库保留原列表路径，旧助手协议与响应字段保持。

## 实际来源与最小增量

从已核验实际dc8镜像的237份捕获输入构造独立候选，仅改三份运行文件：

- `apps/backend/app/services/cn_realtime_entity_state.py`
- `apps/backend/app/services/redis_realtime_speech_repository.py`
- `apps/backend/app/services/realtime_speech_service.py`

237输入数量保持，234份非目标字节和全部文件权限保持；没有从根目录整包构建。完整203条离线OpenAPI及344项离线默认配置与基线相同，161份Python编译通过，连接池仍false。依赖、Prompt、助手d7清单及其它运行输入保持；单独上传格式文件的本地SHA保持。**这轮没有读取生产私有配置，也没有构建/运行新的生产Docker镜像；后续发布仍需实际镜像及私有配置复核。**

## 红测试与规模结果

修复前先执行新增回归，1/1191/10000三种规模均因全站HVALS与逐条HEXISTS而失败；不是只有新代码能通过的展示样例。测试数据全部合成，Redis为独占localhost实例。

| 全站绑定数 | 修复前配对Redis往返 | 修复后配对Redis往返 | 修复后绑定解码 | 权威会话读取 |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 3 | 1 | 1 |
| 1191 | 1194 | 3 | 1 | 1 |
| 10000 | 10003 | 3 | 1 | 1 |

上表包含登记设备的2次HGET；修复前绑定列表为1次HVALS+N次HEXISTS，修复后绑定定点读取为1次EVALSHA。有效pin命中的客户端及服务端HVALS/HGETALL/HSCAN增量均为0。结果不依赖跨请求缓存。

本地单次完整配对耗时为约0.33–0.34ms，但会话仓库为合成内存实现；**不能当成线上HTTP耗时或预估P95。** 12个不同设备混合轮询，1场live、11个ended/idle，10000条背景绑定，带pin/普通配对与控制读取共同执行，总39次Redis往返、本地约8.715ms，全部状态符合预期；未进行生产压测。

## 验证与边界

冻结候选的相关后端回归为**986通过、1项已知Global专属跳过、0失败/错误**（66模块+2个foundation用例；包括新增30项规模/安全测试）。另外两个新增屏障交错测试对同一冻结候选通过：读取前发生退役/重绑时，不能返回旧活跃pin；配合现有end插入定点读取与DB校验之间的用例验证结束保护。独立审查覆盖三文件相对dc8差异，未发现阻塞项。

原有普通/笔试/模拟、鉴权、计费、Redis恢复、慢关闭/取消、截图、多屏、资料及相关Global分支回归包含在选择内；不代表全部国际服或真实设备端到端验证。三个Global-only模块沿既有CN基线缺失限制排除，不混入其源码。全套运行前后237输入SHA及直接测试源保持；网络/环境/候选导入保护启用，独占新建的Redis/PostgreSQL及合成数据库均已按归属清理。

本补丁仅解决高频有效pin分支，不承诺所有后台/list管理读取都已定点化，也不以从指标中删除慢路由代替修复。latest索引缺失时的原修复扫描不在有效pin命中的固定工作量承诺内。线上API P95实际改善未测，原线上问题在发布本补丁前仍可能出现。

[项目规则](../../AGENTS.md)已增加I/O次数、服务端扫描和解码规模回归要求；功能通过不能代替性能规模验证。后续发布必须以届时实际镜像最小增量并重新通过用户工作门禁，保留受保护回退，不能覆盖无关优化或沿用上次残留TCP例外。

## 证据

[237输入与三文件清单](cn-pinned-binding-local-20261104.1/candidate-manifest.json)、[查询成本](cn-pinned-binding-local-20261104.1/query-cost-results.json)、[离线合同核对](cn-pinned-binding-local-20261104.1/offline-contract-verification.json)、[广泛测试](cn-pinned-binding-local-20261104.1/candidate-test-summary.json)、[额外交错测试](cn-pinned-binding-local-20261104.1/race-test-summary.json)、[场景逐项核对](cn-pinned-binding-local-20261104.1/scenario-verification.json)、[独立审查](cn-pinned-binding-local-20261104.1/independent-review.json)、[本地资源清理](cn-pinned-binding-local-20261104.1/synthetic-resource-cleanup.json)。

完整日志、红测试JUnit、候选、3文件patch、guard及runner保存在 `artifacts/cn-pinned-binding-local-20261104/`。本轮不更新Web、助手、Global、worker、模型/Prompt、收费、数据库结构/索引、池开关、依赖或生产配置。尚未部署、没有Git提交/推送。
