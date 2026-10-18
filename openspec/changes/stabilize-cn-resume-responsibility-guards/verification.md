> 当前生产状态：按用户R13要求已恢复10月18日f6dbe的改写逻辑与旧PDF。V6及其各阶段验收留作历史，当前以[完整回退记录](../../../docs/releases/cn-resume-user-rollback-20261019.1.md)为准。

# V6验收记录

状态：本地与实际候选质量已通过，正式生产部署、独立verify与180秒观察已实际通过。使用当前R12及[生产规范](production-release.md)，旧v4/v5失败已停止且保留；未部署旧失败候选。

当前完整受影响回归833/833，0失败/错误/跳过，102.47秒；V6新40纯例+8隔离真实PG案例。此前v5 785/v4 730/原686与此有重复，不相加。QA工具26例；发布控制器最终104例通过。没有将MockTransport/本地fixture称为实际模型调用。

| 实际固定合成case | 模型耗时ms | 安全实质修改数 | 结果 |
| --- | --- | --- | --- |
| named-units-v6-01-campus-practice | 11033 | 4 | 通过 |
| named-units-v6-02-repeated-responsibilities | 8583 | 3 | 通过 |
| named-units-v6-03-crlf-quotes-lists | 17660 | 11 | 通过 |
| named-units-v6-04-normalized-html-table-jd | 17316 | 9 | 通过 |
| named-units-v6-05-long-mixed-technical-terms | 15518 | 4 | 通过 |
| named-units-v6-06-nontechnical-operations | 15452 | 4 | 通过 |

6例各1请求，无自动重试，当前阶段6次，前两阶段实际4+1共本任务11次<=12。第三例连接中断先按只读原服务器marker/receipt/排他锁确认没有触发模型，再继续同一冻结case，未新增或清除模型attempt。旧连接失败记录保留。仅合成Provider直调，无生产job/usage/账本/资料写入，无读取真实用户内容或OSS；生产配置与原日志只留服务器。当前自定义网关为prompt_json，未擅改模型/endpoint或加未知response_format；固定四/五具名评分类型由服务器严格验证与恢复旧公开数组，不补假分。

实际candidate sha256:8c9aaeb46cf7f1cd9d41c886f5407070bb6bb30f16fb2df0cb32d0ddee96fa8b，固定父6f9；完整231→241，仅12运行源，原229不变。完整202schema/340有效配置/315Web静态/NGINX/7非目标核对保持。禁网只读不进入lifespan七副作用0；10已验收CN PDF逐字节同原样14页、Word部件/双get等守卫通过；实际Linux单root只读挂载通过。最终qa verify完整6/6，证据绑定controller/plan/Prompt/来源/case/镜像不可变SHA。有限样本不等于生产长期成功率。

| Spec场景 | 已执行证据/当前判定 |
| --- | --- |
| R1 | v3旧拒绝/v4窄第三方名词接受合成对照，helper/fragment/行格/最终稿纯例与PG成功 |
| R2 | 候选人真实参与/混合/裸参与者/强责任/英文及数字实体技术负例拒绝，窄上下文正反例 |
| R3 | v1–v5旧validator函数AST保持，独立旧Prompt字节保持；v6新fresh版本/未知0HTTP；默认预算不变 |
| R4 | 真实隔离PG/API免费/100积分/partial/0有效退款/重放/修订取消/双get导出案例通过 |
| R5 | 旧v4实际4次后失败停后例，旧marker保留；不计为该阶段8例全通过 |
| R6 | 当前V6实际完整镜像probe241/202/340，229旧输入、模板和7非目标保持；最终生产verify完整通过 |
| R7 | 104发布工具中完整七门禁/TCP/netns/归属/unknown停止/受保护恢复/严格停态证明正反例；实际preflight/切换临近完整保护均通过 |
| R8 | 正式部署、独立verify的9公共检查与180秒346行未截断脱敏观察均实际通过 |
| R9 | v5短正文保留CRLF/list/quote/table位置，旧whole-fragment构造仍拒绝；当前真实CRLF和表格case通过 |
| R10 | 未知/重复/跨格/伪造事实/换行pipe/内部offset/partial/全相交/0有效退款及历史版本全部回归 |
| R11 | v5实际首例schema失败停后7，marker/候选保留不发布；有据协议修正后以R12验收 |
| R12 | v6具名四/五分结构必填/extra/type/JD负例，正规完整转回旧API；当前实际6/6单次全部通过 |

主证据：artifacts/cn-resume-responsibility-20261019/v6/combined-junit.xml、source-and-backend-verification.json、qa/actual-verify.json、qa/actual-evidence.json、release/release-acceptance.json、release/root-payload-verification.json、release/controller-final-tests.xml。正式服务器根和后续状态见生产规范。无Git、Web/国际服/助手或普通/模拟面试更新。

最终生产：actual-deploy.json、actual-verify.json、actual-deployment-evidence.json绑定2ccf5216/8c9候选。observation-final.json记录实际180秒、346行且未截断，同一目标healthy/running/restart0，ERROR/traceback/HTTP5xx和固定/未知失败诊断0；无回退/reload。53保护函数AST与39文件冻结未变。


R13实际完成：目标旧f6dbe，当前容器db1d63010436b4bb38060dbdc885a80db61deab3f4ebd584700fb255693185a6；完整230源/202schema/340配置/315静态与7非目标保持，9公共检查通过；最终观察1792356543491–1792356723491共180秒/394行，4000行上限未截断，同一目标healthy/running/restart0，ERROR/traceback/HTTP5xx及固定/未知失败诊断全0。没有恢复/代理reload/新模型调用/业务测试数据或Git操作。用户数据和已保存稿不回填，新任务与后续PDF下载使用旧版本。证据为artifacts/cn-resume-user-rollback-20261019/，包括root-final-rollback-review.json；双根strict及链接校验在最终收尾执行。
