> 当前生产状态：按用户R13要求已恢复10月18日f6dbe的改写逻辑与旧PDF。V6及其各阶段验收留作历史，当前以[完整回退记录](../../../docs/releases/cn-resume-user-rollback-20261019.1.md)为准。

## Why

上一轮编号定位实现的六个固定合成真实请求中五例交付、一例被责任词守卫拒绝，不能发布。纯合成回归另证实第三方称谓“其他参与者”中的词素可能被误当作候选人的参与职责；该反例不是第六例真实响应或根因。用户现明确要求继续优化、自测通过后上线国服。

## What Changes

- 新v4保留服务端编号及完整Markdown/行格事实防护，仅将明确第三方称谓“其他参与者、其它参与者、其余参与者”中的“参与”排除出候选人有限责任判定；同一行其余“参与/协助/辅助/配合/支持”、裸“参与者”仍受保护，强责任词检查不变。
- 独立v4 Prompt要求保留每行原责任限定、只保守改写非事实措辞，避免模型触发守卫；v1/v2/v3原文件及分支保持，旧结果不回填。
- 新增正负合成评测、回归与隔离PG/API验证；延续上轮编号版本，实际CN固定父镜像增量发布Backend，其他服务/计费/导出保持。
- 本轮另有新的用户授权与预算：冻结八个独立合成质量用例，各1请求且先持久marker，任一失败/未知停止，不自动重采样；旧六次失败记录与marker永不重用。全部质量验收通过才生产切换。

## Capabilities

### New Capabilities

- `cn-resume-responsibility-stability`: v4第三方称谓与候选人责任区分、版本兼容、有界质量验证及受保护单Backend发布。

### Modified Capabilities

无归档能力改写。本变更明确只对v4替代上一轮“全部复用旧责任词子串判定”这一窄规则，其余[编号合同](../anchor-cn-resume-optimizer-references/design.md)及[CN合同](../add-cn-resume-optimizer/contract.md)保持。

## Impact

CN Provider、新责任词helper与v4 Prompt、新评测/测试，以及已开发未发布的编号五文件增量。公共API/数据库/配置/依赖/Web/Global/助手/模拟面试/费用/导出样式不变；不Git、不读取真实用户简历或创建生产业务测试数据。私有配置仅留服务器。用户已授权开发、自测及通过后的国服发布，不再另请求同一部署确认。


## V5 implementation correction after the observed v4 format rejection

V4阶段实际只消费4/8次：前三成功，第4表格case以draft/draft_invalid失败，5–8未开始，旧候选b78及全部marker保留且不得发布。固定原因不能确认具体格式位置或原响应，不能声称看到了模型输出。

当前用户“继续优化，自测通过后上线”授权覆盖有依据的实现修正与重验，不要求再次确认同一目标。本次改为v5短文本编辑单元：完整来源仍按600/200只读编号提供评分依据；服务端从非标题/非分隔/非空白行或表格cell正文建立最多24个、每个8–144字符的可信span，模型edits只含unitId/replacement，禁止返回换行/pipe/HTML/整行前缀。服务器保留所有换行、缩进、标题、列表、引用、表格pipe/边缘空白，仅将短正文按可信位置嵌回，仍逐unit、完整变化行格、最终稿事实及结构验证，沿用v4窄责任谓词；0有效仍失败退款。v1–v4路径/Prompt保留，默认新任务v5。

单元按原行序提取、去除只读prefix及cell边缘空白，正文长于144时优先[40,144]内最后句终止或空白边界，否则精确硬切；不足8的尾段不列可编辑单元但原稿完整保留。候选超过24则按i*(N-1)//23的24个原序下标均匀选择；否则全部选择，选后原序u0001编号。每单元输入重复text最多144字符，24项的结构及最坏转义与原编号开销共同需<=32KiB，原源/JD准入和模型预算不变。位置不发模型、不持久化。

这次是协议/源码/Prompt发生实质修正后的新冻结验证，不是对相同失败候选重复采样。另给v5固定八例各一次预算，总本轮最多4+8=12请求；v5任一失败/未知停后例，不再自动追加/换目录。不得复用旧v4 marker、删旧失败或把本地构造当actualcase4输出。v5预期十运行文件相对实际231为239，原229保持；全部通过后才更新正式候选/发布器精确范围和实际digest。之前七源236与八例描述保留为v4阶段历史，不能作为v5发布输入。


## V6 correction: server-owned dimension names and supported structured output

V5首例实际1请求以schema/dimension_set_invalid失败，后7例未开始，b455及marker保留且不得发布；未见原响应，不推断具体漏项/重复项。V4+V5已消费5次。本轮当前继续优化授权内，用有据协议修正替代重复采样：v6评分dimensions改为固定四字段对象（有JD才为第五roleMatch），每字段只提供score/reason/evidence；服务器把类型完整验证后的对象按固定key/顺序转回原公开数组，再走完全相同的单元/事实/语言等验证，不填缺失分数、不删多余字段、不造默认成功。用户输入显式requiredDimensions由JD决定，targetRole不能创建JD维度，Prompt包含完整四字段JSON示例。

v6沿用v5短单元和v4责任规则。仅新v6请求温度0并按[阿里云官方结构化输出说明](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output)选择参数：明确官方中国DashScope且明确文档支持的qwen3.7-plus/flash/max、qwen3.8-max/flash系列用strict json_schema；其它明确官方Qwen文本接口用json_object；未知自定义网关不擅自增加response_format。全部分支仍服务端严格完整验证，JSON Object只约束JSON语法，不宣称保证结构/事实。模型/endpoint/密钥/环境不更改，原90s/6500/256KiB/并发/一次模型调用与费用不变，原v1–v5保留。

v6新增独立schema/Prompt两源，当前相对实际231为12源增量/241总输入，原229保持。完成全本地/PG/接口导出/实际禁网先验后，本轮最后一次冻结6个核心质量case（校园/重复/CRLF/表格/技术/运营，包含两种既往失败材料），各1次，合计5+6=11且不得超过12。不是旧候选重采样，旧失败marker和剩余未执行计划保持；v6任一失败/未知停后例，不能随机续调，全部6成功才发布新固定镜像。新增QA-only安全形状/固定拒绝统计，只有枚举计数/HTTP状态/阶段，不保存或输出原响应/正文/动态key，不能用它回溯未见的旧输出。之前v5八例计划已停止，不作为当前通过/发布条件；当前以本追加及R12为准。


## User-directed quality rollback (R13 overrides v6 production target)

2026-10-19用户反馈最终输出不整齐、不如昨天，明确要求“改写逻辑和 PDF 模板都恢复到昨天”。本轮不继续修改AI规则，按旧正式发版固定image sha256:f6dbe8fd498f1f965bf8ba611d666e7ea49475ac1a7bf01b547ed79e8c6bbfaa恢复v2改写与旧shared PDF排版。今天v6合成调用/安全通过不代表用户认可最终整体可读性，旧验收和失败均留历史，不能以其阻止本次已授权回退。

新鲜只读实际基线为2ccf5216/8c9、241输入，SHA718f4783545b229cd6dcedd77cd7e68bbb2c5c804d68d07628a1f38d9a00add4。目标是10月18日最后正式Backend f6dbe的230完整输入：撤回13路径变化（11新增不再在目标镜像、2旧文件恢复），原228输入保持。202完整schema/340有效Settings/315Web静态/7非目标/费用/模拟面试保持。无应用源码实现/构建/模型/DDL/数据恢复/Git，不删除今天的用户资料、优化任务/已保存稿或账本，不重放历史任务、不自动把旧结果重新优化；新任务恢复v2，已完成v6结果按相同public wire读取和旧PDF导出，需纯合成禁网验证。

该行为为用户明确选择的产品质量回退，不属于无依据自动故障恢复；使用新独立发布根/计划/真实基线，不篡改旧prepared/progress或覆盖旧控制器。新控制器仅调整输入/prepare/镜像probe/verify_current，原53完整归属/配置/Mounts/image-only切换、重复七门禁、真实TCP/netns、未知停止及严格停态恢复保护函数AST保持。使用当时已发布固定不可变镜像，不从旧目录重建；核对原Config与目标是当前镜像实际祖先，探针230完整源/202schema/340配置、真实合成Word/PDF/新旧已存稿兼容、七副作用0。新的known健康失败仍只在相同保护下恢复本次冻结8c基线；漂移/未知停止。正常user回退必须当前Running/healthy并实际TCP0，忙碌等待真实用户结束、不清活动/放宽门禁。

服务器根/证据：/opt/offersteady/releases/20261019-cn-resume-rollback-1；artifacts/cn-resume-user-rollback-20261019/。预检查与临近切换均完整七门禁+实际TCP/netns，全量功能/配置/Web和7非目标保持；独立verify/9公共检查和实际180秒脱敏观察后才报告恢复完成。新记录明确旧v6部署已被取代，保留研发工作区且标明非线上，不能自动再次发布v6。
