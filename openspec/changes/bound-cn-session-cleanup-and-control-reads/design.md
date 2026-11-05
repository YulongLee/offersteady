## Context

基线是封版release-20261104.1中的国服a1e6实际237运行输入；14:41只读六文件来源核对一致。本轮仅本地，不再访问服务器。根目录还有先前未发布的screenshot配套，必须隔离。诊断见[下午记录](../../../docs/diagnostics/cn-api-p95-20261104-700ms.md)。用户已授权实现及自测，状态apply-ready；部署、Git推送和Global适配不在本轮。

## Goals / Non-Goals

降低用户查询随全站历史增长的I/O、避免关闭握手阻塞新连接准备、减轻遥测授权的资料装配成本。保留权限/结束/计费/字幕/模型/协议及Global/mock原路径；不改Web、助手、配置/依赖/SQL/池，不承诺将空闲44ms复现为真实并发P95。

## Decisions

1. **作用域读取。** 单场结束使用现有owner/session canonical getter。为用户绑定和账号关联建立两个全局hash索引，每个owner字段保存该owner的canonical字段集合；查询Lua只读当前owner集合和对应数据及退役状态，返回原JSON字节。索引与canonical写在同一Lua操作，沿原共享TTL续期，无跨请求资料缓存。已有实体在仓库初始化、旧snapshot seed后一次原子建立索引及ready标记；正常命中不得HVALS/HGETALL/HSCAN全站。缺失ready按错误失败，不在请求中静默全扫。保留stale历史、generation、原始精度和数组。索引仅含原有标识引用、不含正文，寿命不长于兼容运行态策略。
2. **最小物理关闭隔离。** 不另造持久任务系统，不把计费/会话结束放后台。保留原同步结束事务、退役fence、publisher/queue清理；只有已从ASR会话表移除且closed=true的具体旧连接，其物理close握手可进入独立有界执行器（2 worker、8待处理）。满载/关闭后同步退回关闭，不能丢资源或无限排队；新连接对象绝不能被旧任务按session键找到并关闭。shutdown排空已接纳关闭，错误只记录固定计数并保留原错误隔离。Gateway原close_session/close_source保持同步；新增可选deferred方法仅CN普通RealtimeSpeechService选择，Global、mock及旧/假gateway继续原路径。如此无需改变结束接口的成功语义或持久化清理job。
3. **准备通道隔离。** 现有CN I/O执行器新增独立有界preparation通道（2 worker、8待处理），仅publisher_prepare/create选择；ingress和lifecycle原容量保留。继续原取消drain/晚到创建一次补偿与同场cleanup-lock，防止慢逻辑清理阻塞读准备。
4. **回执轻读。** 仅CN performance-ack改用已有权威control投影校验归属；旧仓库无方法回退原get_session。原缓存键/期限/跨owner拒绝和所有回执字段、频率保持，INFO下不为DEBUG回执构造日志JSON。Global分支保持原行为，不改问答/资料刷新业务。
5. **验证和来源。** 先红测试复现N+1、慢close和ACK装配，再真实独占本地Redis验证1/1242/10000历史与服务端命令；混合6/10场合成并发和慢close下准备/结束响应、容量、重绑/退休/关机及费用/权限回归。以固定237来源叠加允许文件构造候选，完整203 Schema/344 Settings/44依赖与d7清单保持，非目标文件逐字校验。AI行为不变，无新增模型评测需求。所有数据合成，禁止真实网络/用户资料；完整suite需要的本地PG/Redis均新建专属实例并清理。

初始化会在每个仓库启动时从canonical原子重建引用，兼容以后空闲回退到旧writer、再切回候选的情况；不依赖旧ready标记猜测当前数据版本。正常请求通过owner计数与全局hash长度的常数校验检查索引完整性，没有全站遍历。完整共享过期且两份canonical均不存在时，读取返回空列表、新写建立空索引；局部丢失或损坏失败关闭，不在请求上修补扫描。

## Risks / Trade-offs

- owner索引TTL/初始化错误 → 原子迁移、并发新写、跨owner流量延寿及过期/重启测试；索引缺失不返回不完整结果。
- 逻辑关闭后物理连接短暂存在 → old-object-only执行、闭合事件条件、晚帧/回调和关闭失败/满载/排空测试；计费和退役必须在接口成功前完成。
- 更多线程增加CPU → 固定小容量、饱和回退，混合回归记录CPU与操作数，不用无限线程绕开慢路径。
- 上线来源不等于根目录 → 本轮生成独立候选；晚上另获授权后重新核对生产组件和全部空闲门禁，不重放旧控制器。

## Migration Plan

本地冻结实际公开来源 → 复现 → 作用域读取/关闭隔离/ACK轻读 → 本地规模与回归 → 来源/合同/Spec审查 → 报告结果等待晚上发布指令。

## Open Questions

无待用户决定的产品行为；关闭队列容量满时明确保留同步关闭回退，不能声称所有过载情况下结束均立即返回。

## Production appendix 2026-11-06

用户已追加国服发布授权。新鲜核对a1e6/7663实际237输入，source与本地冻结来源一致；以实际镜像只COPY已测六改一增文件，238输入/231原输入保持。固定回退为同一a1e6，专用目录20261106-cn-cleanup-control-1、控制器release_cn_cleanup_control.py，不重放旧控制器。

控制器以已审查release_cn_pinned_binding.py为基础，仅更换固定来源/七文件清单及两处范围计数；除check_candidate_scope/verify的预期计数外，全部生命周期函数AST保持。七项原门禁、CN实体只读门禁、TCP0、单writer和归属保护原样继承，恢复也重复；没有旧连接例外。完整私有配置及原始日志只留服务器。

实际镜像以network-none/read-only/cap-drop/无lifespan的合成探针核对完整输入/配置/运行依赖/Schema/辅助格式/d7，以及新owner读取派发、四类ACK、两个lifecycle worker忙时独立准备、取消补偿、旧对象关闭及提交失败只执行一次。真实Lua规模结论仍来自本地独占Redis，镜像探针不接生产Redis/PG/模型。切换后独立verify、真实来源验收及短时脱敏自然流量/错误观察；无真实样本不补造性能收益。
