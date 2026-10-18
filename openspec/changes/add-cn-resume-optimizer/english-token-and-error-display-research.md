# 国服英文词保留与失败说明展示研究草案（11.x）

状态：仅研究/规划，未发11.x实施GO，不进入业务实现或生产动作。当前回合回答用户“为什么上线后仍然失败”；下述修正是待评审方案，不代表已经开发、修复或发布。9.x本地、10.x生产上线与当次验收的已执行事实保持；OpenSpec strict通过只证明文档结构有效，不等于本草案已获实施批准。

## 已验证事实与证据边界

已上线Backend `sha256:6f2a53f55ac6343c983234fedde62bd46432a1087c75705425c267971bf3d581`、容器b955c33e…仍healthy/重启0。用户后续一次任务已读取3437字符、无JD，28030毫秒后失败；固定诊断为facts/fact_english_content_added，表示某条改写增加了该sourceQuote中没有、且不在原允许清单内的英文内容词。收费与退还各一笔-100/+100、usage released，净扣费0。此阶段不是上传/MinerU未解析；不得据此要求重新配置解析API。

模型原始输出没有保存，不能查明具体新增词、断言是API/技术/机构、判断哪条原句被修改，或声称拿到了用户原文。当前诊断也不能独自证明AI虚构了真实经历：严格词守卫还会拒绝部分看似近义的英文格式变化。所有例子必须是另行定义的纯合成资料，禁止读取用户正文/原始模型输出作夹具。安全元数据证据为原仓库`artifacts/cn-resume-optimizer-repeat-failure-20261018/repeat-failure-metadata.json`。

另已确认真实Web镜像20d6a03a…的已编译ResumeOptimizerPage不读后端errorMessage，失败区只查本地errorCode映射；invalid_output又无对应映射，所以虽服务端已有固定原因，页面仍只显示通用失败。此前10.x后台API/单一合成Provider验收真实通过，但没有覆盖这条Web失败展示，不能把它写成用户已经看到了原因。

当前CN v1 Prompt虽要求英文内容词保留，仍未充分强调“每条sourceQuote自己的词集合”。原词守卫保持；14项纯合成研究证明2项语法/大小写变体允许、12项新增词/格式或事实升级拒绝。该证据不定位用户实际新增词：`artifacts/cn-resume-optimizer-hotfix-20261018-release/one-shot-provider/english-token-research-20261018.json`。这些本地合成研究未调用真实模型或改动业务/Prompt源码；生产故障诊断只使用root先前取得的安全元数据。

## 待评审方案：独立CN Prompt v2对齐原守卫

保留v1，新建`ai/prompts/resume-optimizer/review.zh-CN.v2.md`；Provider只调整PROMPT_VERSION为resume-optimizer-zh-CN-v2及加载路径。新任务记录v2，历史v1任务/结果不改，公共字段形状、schema、预算/超时/并发、退款及事实代码保持。预计以当时实际229项Backend输入为基线，仅Provider既有两处接入及一个新增Prompt，形成230项候选；实际数量和来源必须重新确认，不能将此预期当作已实现清单。

v2须明确每个edit.sourceQuote独立约束，英文技术/产品/实体/缩写等内容词按该逐字连续引文保留，不从同段、其他项目或JD借词，不把中文“接口”扩为新增API。组合、空格、连字符、单复数、数量等不作近义改写；可仅调整它们周围的中文，或选择唯一、不重叠且保留角色事实的完整原句，不能借扩大引用把另一经历的事实迁移过来。格式反例可用SpringBoot→Spring Boot、REST API→REST APIs、Python-based→Python，必须明确它们仅是规则示例，不是候选人事实，不可注入简历。旧的普通英文语法连接词/保守动词语义保留，不新增SAFE词、别名或放宽守卫。

无法安全改写时模型可返回edits=[]，仍须给出有效评分/建议/待补事实；不改变该既有合法产品语义。应用层不得自动删除不合格edit、吞掉校验错误、以原文/空edit假成功或自动重试。新增AI eval覆盖同quote原词保留、同段/跨段/JD借词、格式变体和技能/实体/责任正反例，保留全部现有事实测试。

## 待评审方案：固定安全失败说明真实可见

最小Web源范围为resume-optimizer-client.ts的固定helper及ResumeOptimizerPage失败区调用，不改API/wire、其他功能或页面布局。按任务errorCode精确分组固定中文基句；只接受与本地已审核常量完全匹配的errorMessage，或其后严格一个固定退款后缀且权威allowanceStatus为released的形式。返回本地常量基句，不直接回显服务端动态字符串；退款继续由现有权威费用状态区域单独展示，避免重复或虚假退款说明。

unknown code、未知句子、private/对象/异常原文、任何前后拼接或退款状态不一致一律安全通用回退。不给HTML、Markdown或内部stage/reason/payload任何特殊展示权限；原跨账号/private,no-store、取消、重试需用户主动确认和付费确认保持。应覆盖异步轮询失败与历史记录重新打开；既有隐私哨兵负例必须继续通过。

真实Web必须基于当时实际20d6a03a…镜像及305项静态重新冻结，只追加新Page及所需引用资源，主入口/依赖图仅做经审核的URL替换，四入口HTML只换module URL、构建标识按需要更新；全部旧hash/页面正文/媒体/SEO/价格/CSS/NGINX和普通/模拟/笔试导航保持。不把本地完整dist替换线上，不重建无关组件。实际组装产物的Chrome失败场景和隔离NGINX读取须验证，wire或源码单测不能替代。

## 待评审自测和真实合成QA范围

先完成本地Provider/Prompt/evals、Web固定消息/隐私/退款/历史与轮询回归、适用原功能、typecheck/build，以及实际静态组装Chrome和候选隔离探针。生产或真实模型测试都须等待明确11.x实施GO及冻结候选；目前不执行。

若后续GO，真实Provider QA拟最多3条固定、独立、约3千字符的纯合成技术Markdown简历，各至多1次请求；包含同quote词保留、同段/跨项目借词和中文接口/英文格式风险，资料不来自用户。沿用原预算/超时，直接Provider、不建job/usage/账本，不访问钱包/OSS/真实资料。每次前复用完整七门禁，调用前消费与候选/Prompt/脚本/用例绑定的单次marker，只保存固定安全结果/原因/时长/计数及draftChanged等无正文摘要。

这3例须核对至少能产生真实、事实合规的中文局部修改，而不是仅靠空edits让验证通过；此项是刻意可优化合成样本的验收，不把生产合法edits=[]改为错误。任一失败先停止并报告固定原因，不盲重试或改输入碰运气；新的修正需证据、对应eval/回归和重新冻结，不能自动追加模型请求。3例成功也不证明用户原失败任务已成功或所有模型采样可靠。

## 待评审生产边界

未来发布仍需从当时实际Backend6f2a53f5…和Web20d6a03a…分别重新冻结完整源码/202路由schema/340Settings/305静态/配置及非目标。仅批准的CN Prompt及其最小接入、Web固定失败说明增量；无收费/日次数、DDL/环境/依赖/模型预算、Global/助手/Admin、资料处理、钱包或Git变更。沿用完整七活动/金融/CN优化门禁、完整canonicalMounts/非目标签名、固定镜像/归属、Backend→Web及受保护回退和独立验收，不终止用户活动或清理记录制造空闲。只有Backend IP实际改变才允许既有代理nginx语法检查后reload的原窄例外。当前不开发额外发布工具，也不指定已使用的新服务器目录或候选SHA。

## 后续明确开发授权（本文件保留为研究历史）

用户现已要求按讨论的优化点开发。当前可测试合同为[安全局部改写与失败说明](safe-edit-application.md)：新增逐edit独立拒绝/全部合格重叠剔除/有效修改才交付/无有效修改失败退款及安全计数。本研究原“不筛选edit、合法空edits可成功”并非新合同限制；先前未实施的事实保留。11.x仍须root独立strict实施GO，本轮只本地开发/自测/预览，不生产切换。
