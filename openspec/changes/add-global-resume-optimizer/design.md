## Context

Global 已有英文资料库、上传/解析、账号归属、私有对象下载和面试材料快照。2026-10-17 已发布鉴权与状态读取优化；该运行镜像及实际 Web 构建必须重新绑定后才能作为本轮生产基线。新功能包含敏感个人资料、独立模型调用和导出，不能把负载放进实时回答工作流或覆盖原资料。

用户已批准本轮国际服开发、自测和上线；国服同步需后续国际服验证及单独授权。用户最新确认国际服只使用时间会员，不用积分：所有有效付费时间会员（包括 1 天套餐）按 UTC 每日免费优化 1 次；非会员提示升级会员，当日超额提示次日再试；失败/取消退还创建日次数，编辑、导出和另存不再占用。其他 Global 权益、面试配额和 Creem 行为保持。

## Goals / Non-Goals

**Goals:**

- 自有简历 + 可选 JD/目标岗位 → 有依据的参考诊断 → 用户可编辑优化稿 → 真实 DOCX/PDF → 用户确认后另存简历。
- 原资料、AI 建议和用户修改保持可区分，原简历/面试快照不被替换。
- 自有任务有明确状态、可靠持久化、严格权限、删除传播和有限资源；所有界面为英文。
- 增量发布 Global Backend/Web，保护现有 Global 独立账户、语言、Creem、收费、模拟面试开关和既有优化。

**Non-Goals:**

- 自动投递、招聘评分保证、隐藏录音、图像简历设计器、模板市场、多模型自动路由、国服/助手/Admin 发布、校园大使、支付/会员规则调整。

## Decisions

### 1. 独立功能域，复用受控资料读取

新增 `resume_optimizer` module/schema/service/repository 与独立的 PostgreSQL 表；必要的路由/配置/依赖注册以最小节点补丁接入。API 统一 `/api/v1/resume-optimizer`：capabilities、创建/列表/读取/取消/删除 job、更新 draft、另存 material、下载 DOCX/PDF。路径已由 root 冻结；最终字段合同由 root 在实际基线核对后冻结，变更需同步本设计再实现。

输入由 `sourceDocumentId` + `sourceVersionId` 锁定 owner 的 ready resume；JD 可以是 owner 的 ready JD 版本或用户显式粘贴的限长文本，目标岗位可选。只读取解析后的受控正文，不在优化 worker 重新运行 Parser，不改变资料索引/收费。未 ready、已删、版本失配、跨账号或类型不符均拒绝；无法读取正文时提供可恢复错误。复用现有上传页面/控件，不新增上传格式或直传安全边界。

既有 MinerU 规范化 Markdown 可以含 HTML 表格。优化功能的输入读取边界 SHALL 仅在内存中通过 `HTMLParser` 将受控 `table/tr/td/th/tbody/thead/tfoot/br` 标签转换为按行/单元格有分隔的纯文本/Markdown，解码实体并保留每个单元格的全部可见文字、数字、日期、联系方式和结构顺序；不能用简单删标签正则拼接单元格或静默丢失内容。输出的同一规范化副本用于任务 `sourceText`/JD快照、证据 quote 校验、模型输入和基于 quote 的局部改写，避免分数证据与用户看到的源文不一致。转换只涉及本次优化输入，不写回旧 Parser 的 `normalized.md`、原文件、资料版本或已有面试快照；正文界限在规范化后重新验证且不截断。

不支持的 HTML（包括 script/style/可执行或外部资源标签、非法结构）在预留次数和模型调用前拒绝，返回固定英文可恢复错误，提示改用纯文本或重新上传；不得执行脚本、解析 CSS、加载 URL、访问远程资源、丢弃未知内容后继续生成。导出/用户编辑稿仍执行既有纯文本/Markdown限制，不开放模型 HTML渲染。

替代方案：直接把简历优化接到 ChatAnswerTask/实时队列。放弃，因为其计费、取消和面试语义不同，容易竞争面试资源。

### 2. 持久化有限任务与可见状态

任务保存 owner、源/JD 文档版本、输入摘要、状态、输入必要快照、结果/编辑稿、revision、创建/更新时间、Prompt/模型版本、可脱敏错误码及幂等键；不保存完整 provider payload。任务状态为 `queued/running/completed/failed/cancelled`，用户删除后任务不再可读。列表只返回摘要；正文仅 owner detail 返回。

同账号同时最多一项未完成任务，全服务默认最多一个执行任务；队列、输入字符、输出字符、轮询频率和模型耗时都有服务端上界，满额明确返回 busy 并允许重试。使用独立执行器/可替换 provider，不占面试回答执行池或触发 ASR/RAG；配置现有模型端点的独立客户端/超时，不修改实时模型、Prompt 和供应商配置。状态持久化且 claim/update 使用数据库条件更新，重启将过期运行任务标为可重试失败，不盲目重复调用模型。

取消/删除/源删除必须同时改变持久状态，运行任务即使模型稍后返回也不能保存/恢复已删数据。发生超时、网络错误、协议/语言/事实校验错误时仅保存脱敏错误，不能伪装成功或输出残缺稿。用户显式重试创建新 attempt，幂等创建重放不重复排队。capabilities 与创建由服务端统一判断真实有效付费时间会员状态、UTC 当日剩余免费次数和任务容量，所有套餐（含 1 天）一视同仁，不沿用模拟面试七天购买准入。会员状态以现有实际 Global 有效权益为准，不按前端标签或虚构资格判断；不新增积分、钱包、价格报价或付费购买入口，也不使用 Creem minutes/模拟面试配额。

创建确认时在数据库事务内原子预留创建日的一次资格，幂等重放不重复占用，只有 completed 完成交付后记为 used。失败/取消/源删除导致不可交付时原路释放创建日预留且 exactly-once；跨 UTC 午夜释放不增加新一天额度。非会员明确返回 upgrade_required，当日额度用完返回 daily_limit_reached 并给出下一次 UTC 重置时刻，不调用模型。用户显式重试需重验当时会员及创建日新额度；编辑、再次读取、下载和另存已有稿不要求新增优化资格、不占次数，未删已完成结果在会员到期后仍可由 owner 访问。

替代方案：只存在进程内或不限量 FastAPI background task。放弃，因为重启丢记录、队列无界和取消后重现资料不符合任务及隐私要求。

### 3. 有依据的结构化评审与可编辑输出

专属英文 Prompt 位于 `ai/prompts/`，将简历/JD 标为不可信资料，禁止执行其中指令。模型返回受 schema 约束的数据：参考总分及维度分、每项理由/原文引用、按优先级排序的建议、事实缺口、结构化优化稿。无 JD 时岗位匹配项标为未评估，使用明确版本的权重计算总分；分数限制为 0–100，页面标识为本工具参考标准而非录用概率。

服务端验证结构、长度、分数范围、原文引用确实存在、所引用的来源类型与可用输入一致。经历/技能/学历/日期/成果数字必须来自原简历，JD 只作为岗位要求；缺失信息以明确待补充项呈现，不能把 JD 技能或模板示例变成候选人事实。输出不能通过校验则失败，保留原文且不生成可下载的“成功”稿。新增合成评测覆盖空缺、冲突、多语言、数字保真与注入。

编辑稿使用纯文本/结构化段落，不渲染模型 HTML；用户明确修改后以 revision 乐观并发保存。原文与 AI 初稿保持可比较，用户编辑只改变 draft。页面提示用户核实所有内容并允许删除整个优化任务。

替代方案：自由 HTML 或仅文字建议。前者增加注入/导出风险，后者不能交付可投递简历；因此选择结构化结果 + 可编辑纯文本模板。

### 4. 导出真实文件，另存明确分离

DOCX 与 PDF 从同一份已保存编辑稿、同一简单英文模板生成，标题/项目/日期/列表使用标准文档结构。导出通过认证 API 流式返回附件，正确 MIME/扩展名且无公开链接、脚本和远程资源。PDF 必须是真实 PDF 字节及可读排版，不能改名 HTML 或只提供浏览器打印；DOCX 必须可被标准文档工具打开。导出由 root 负责独立格式模块，采用服务端真实 DOCX/PDF：DOCX 以标准库生成 OOXML，PDF 使用固定版本 ReportLab 4.4.9 和 OFL 许可的 Noto CJK TTF 字体；root 安装并对实际镜像、字体许可与双格式排版做 QA。Backend 任务服务继续负责 owner/job/draft 权限，格式模块只接收已授权的纯数据，不自行查资料或暴露文件路径。

另存由用户显式确认，基于最新已保存稿创建新的 owner resume，返回新 document/version；可重放请求返回同一新资料，原简历及既有面试快照不变。成功后的资料按现有 Document Service 解析/选择边界交接；不能只插入前端假资料或保存无法被面试读取的记录。

替代方案：覆盖原文件或生成一次性下载链接。前者破坏既有快照，后者增加隐私清理范围，因此不采用。

### 5. 删除与最小保存

任务创建页说明简历/JD会发送至当前 AI 服务、结果随任务保存及可删除；既有“原始音频默认不保存”的承诺不变。日志只记录状态/耗时/计数和安全错误，不输出姓名、联系信息、正文、对象 key、Prompt 或 provider payload。

任何 task 操作（包括 list/detail/draft/export/save-as）在服务端校验 owner；异用户/失效 token 不泄漏内容。删除源简历或引用 JD 后，关联任务立即取消/不可读，派生输入/结果/草稿和缓存导出实际清理，后台完成采用状态+revision 条件写入以防复活。任务删除同样清理。独立另存的新简历由用户确认创建后遵循正常资料删除规则，界面明确它与任务的区别；删除任务不静默删除已被用户明确另存的独立资料。

### 6. 实际镜像基线与受保护发布

root 只读抓取 Global 各目标组件实际运行镜像的完整源/Prompt/路由与有效配置摘要，构建候选只叠加批准文件/节点。新迁移必须 additive、幂等，无批量读取/修改真实简历，旧业务表不变。新增 API 在原215条实际完整路由上增量，不能用离线 shell inventory 替代。Web 使用现有实际源/构建基线并保持原路由/商业配置。

本地使用合成资料、受控假模型和本地隔离 PostgreSQL，完成鉴权/删除/并发/失败/导出/页面与回归检查，实际镜像探针在无网络只读边界核对安装和路由。不得进行真实用户测试数据导出、生产压测或真实面试创建。发布前后重复活动门禁，活跃普通/模拟/笔试/音轨/回答/资料任务或未知状态均等待，不结束用户会话。仅在空闲且预检通过时按固定镜像增量发布 Global Backend/Web，冻结原环境及反向代理并保留回退；其余容器、CN、Admin、助手保持。失败恢复仍受活动/归属保护。

## Risks / Trade-offs

- [模型产生貌似合理的错误] → 结构化 schema、原文引用验证、事实约束 Prompt 和评测；事实不确定显示待补充，用户最终确认，分数明确参考。
- [模型推理占用共享供应商容量] → 单执行并发、独立队列/超时/客户端及可关闭开关；上线短时观察不等于真实容量证明。
- [删除与后台完成竞态] → owner/source复核、数据库条件提交和物理清理回归，不允许任务复活。
- [简单模板与用户原排版不同] → UI 明确导出为标准优化模板，保留原件下载，先保证可编辑与内容完整。
- [新文件依赖导致运行失败] → 实际候选镜像安装/离线 DOCX/PDF 内容及排版验收，发布前发现即停止，不用假PDF代替。
- [会员到期、并发任务或跨日导致资格误算] → 创建时审计实际有效付费时间会员；UTC 日期与 job 绑定，原子预留/完成/释放且幂等，不借用分钟余额或面试配额。

## Migration Plan

1. 冻结实际国际服基线、已确认的会员日额度政策和接口合同，严格验证 OpenSpec。
2. 本地独立功能开发、Prompt/evals、additive migration及合成数据库/页面/导出测试。
3. 核对所有既有 Global功能和当前性能补丁，再构建 Backend/Web 固定候选。
4. 空闲门禁后运行幂等迁移并发布国际服，验收新路由/公开页面/健康/配置与非目标身份，保存脱敏证据。
5. 失败时先关闭新入口，再按活动保护切回固定原镜像；新增表保留且不可访问，不执行破坏性 down migration，不删除用户资料。
6. 用户在国际服验证后再评估国服；本轮不更新国服、不承诺未经测量的长期 P95。

## Implementation Contract Handoff

- 会员/收费决策已解决：Global 有效付费时间会员（含 1 天套餐）UTC 每日 1 次，不用积分；真实权益查询绑定既有 Global 服务。
- Backend agent 在 `contract.md` 冻结最终字段；统一 `/api/v1/resume-optimizer` 与服务端 DOCX/PDF 已确认，root 在合同文件完成后下发实施 GO。ReportLab/字体实际镜像安装和 QA 属于执行验收任务。


### Approved parsed-table normalization refinement

Only the optimizer input reader converts recognized inert MinerU HTML table markup into bounded plain text using HTMLParser; the old parser, original files and normal material processing stay unchanged. Cell text/numbers/contacts are retained in order with column/row separators, and the same normalized copy is used for displayed source, literal evidence, provider input and draft. Unsupported/malformed markup or active-resource attributes fail before quota/provider admission with clear English guidance rather than silently discarding data. See the controlled-table section of [contract.md](./contract.md). Synthetic full create→generation→evidence→real DOCX/PDF tests cover preservation and injection/rejection.
