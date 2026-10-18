# CN片段引用v3本地执行记录（真实质量未通过）

状态：**真实纯合成质量5/6成功，第6例失败，Q1未解决，当前候选不得发布。** 全部6例各1次请求、6marker已消费、无重试/剩余额度；verify以prior_case_not_successful拒绝，不能写成验证通过。原国服Backend6f9、7非目标/Web/配置保持，生产切换/业务测试写入/Git均0。本地代码、686回归、隔离业务验证与真实结果记录已交付，任务执行7/7只代表执行/文档收尾，绝非质量验收成功或发布GO；独立最终审查证据完整但qualityEvaluationPassed=false/releaseRecommended=false。

## 已取得事实与非目标

本轮只读实际基线`artifacts/cn-resume-optimizer-anchors-20261019/current-baseline.json` SHA`ae973bcfb50949682459afe2ca744bcc673b8727e201af9488d3de0b8a75df70`：实际Backend2a907/6f9a healthy/restart0、全部231输入与CN工作区逐字匹配，202完整schema/340Settings/315Web静态和7非目标/配置保持。原已上线[商务PDF记录](../../../docs/releases/cn-resume-delivery-template-20261019.1.md)及原失败/安全局部历史保持，不将旧测试或180秒观察计为本轮新验证。

原source40000/JD12000/targetRole120/draft60000、24edits、90秒/6500输出tokens/256KiB响应、1Provider/8unfinished和会员3次/100积分保持。本轮只允许CN定位/schema/Provider/最小版本传递、v3 Prompt/evals及隔离合成测试；无Web/UI/Global/助手/模拟面试/PDF样式/DDL/配置/依赖/收费改动、Git或生产切换。

## 当前源冻结和阶段实际验证

两份阶段证据与根最终合并报告均绑定下列相同五运行源；`local/spec-evidence-binding.json`是合并前读源证据，根`root-source-preservation-review.json`再次完整确认：原231输入仅Provider/service两项变化，其余229逐字保持；新增anchors/internal v3 schema/Prompt三项，完整运行输入234。原legacy schema、repository/金融/诊断/source normalizer、v1/v2 Prompt、商务renderer/shared helper/字体、Web与所有其他输入保持。实际隔离QA候选的禁网证明另见下节，不得将本地hash或QA候选冒充生产已切换。

| 运行源 | SHA-256 |
| --- | --- |
| apps/backend/app/services/cn_resume_optimizer_anchors.py | 93f5dee46a5e9fe85f0f5f7ac565af6e62521e24bc3d293bd4f681d0e7f80c50 |
| apps/backend/app/schemas/cn_resume_optimizer_provider_v3.py | 2ce9dbaaf32488e5a333c6f85b03bd0bf123fa77006ee4ae83ee2c979c761e75 |
| apps/backend/app/services/cn_resume_optimizer_provider.py | 149908a1a92a4ba0b7fe7328800fabebde8d252a546a58d0b9305c5255113a63 |
| apps/backend/app/services/cn_resume_optimizer_service.py | 82d43d5262428ae71da9fef223ceef3dd8a37b560799d4839c03d300787bfbfc |
| ai/prompts/resume-optimizer/review.zh-CN.v3.md | c18ed5e8544f85de1981382f14532dee73e41ddad7d4b1f01ba8b95d8031de06 |

- `local/backend-pure-first-freeze.json`：实际**338/338**，259旧Provider/诊断/安全局部案例和79新片段/v3案例。工作目录CN apps/backend，命令为`PYTHONDONTWRITEBYTECODE=1 <root>/.venv/bin/python -m pytest tests/test_cn_resume_optimizer_anchors.py tests/test_cn_resume_optimizer_provider_v3.py tests/test_cn_resume_optimizer_provider.py tests/test_cn_resume_optimizer_provider_diagnostics.py tests/test_cn_resume_optimizer_safe_edit_provider.py -q`。原事实checker AST保持，旧count路径原样，未安装依赖；原Starlette TestClient/httpx deprecation warning保留。
- `local/independent-eval-pg-review.json`及`independent-eval-pg.xml`：实际**190/190、0失败/0错误**，73项eval/meta（72份合成eval为17接受/55拒绝，加1元检查）、33项新真实隔离PG/API、22项既有safe-edit和62项既有CN service。命令为`CN_RESUME_OPTIMIZER_ANCHORED_WIRE_OUT=<artifact>/local/independent-anchored-wire.json PYTHONPATH=apps/backend:apps/backend/tests <root>/.venv/bin/python -m pytest apps/backend/tests/test_cn_resume_optimizer_anchored_evals.py apps/backend/tests/test_cn_resume_optimizer_anchored_integration.py apps/backend/tests/test_cn_resume_optimizer_safe_edits.py apps/backend/tests/test_cn_resume_optimizer_service.py -q --junitxml=<artifact>/local/independent-eval-pg.xml`，原第三方warning同前。该组使用真实Provider配MockTransport、隔离真实PG和HTTP API，**不是真实模型请求或生产测试**。
- 前述338/190只作为分组执行历史，不能直接相加并称完整总数，也不能再加到最终686。根`source-and-backend-verification.json`、`combined-junit.xml`/`combined-output.txt`实际重新执行15文件合并集合：**686/686、0失败/0错误/0跳过、约74.87秒**，原Starlette TestClient/httpx deprecation warning1项。命令为`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<CN>/apps/backend:<CN>/apps/backend/tests .venv/bin/python artifacts/cn-resume-optimizer-anchors-20261019/run-combined-tests.py`；非loopback Python连接被阻断，只用本地合成PG和MockTransport，不是真实模型/生产请求。JUnit SHA`cd9ac912947ad66d986bc089fec64ab696047646369191d82a863b7b3fc67f7c`，output SHA`8fa05bca1a5143f9049ee278b2f44d0881fbd123908411d1967533bd16df9373`。
- 根`root-source-preservation-review.json` SHA`0500fe3fd954092ec7c9eb0f8b175189bdf408dbd137287e6605f147313ba25c`独立核对：原fact checker每个AST statement完全相等、legacy safe-edit选择原路径后的完整AST相等、报告所列原函数AST保持，service整模块仅fresh promptVersion传参，229非目标/公开schema及商务PDF源保持。本地新总234，原202schema/340Settings/Web315/7非目标的生产运行事实仍来自fresh ae973…，本轮没有重启它们或重新执行Web/browser/build。
- 已读实现和独立证据：generate直接默认v3，新create版本v3；Runtime仅增加fresh payload的promptVersion参数，旧v1/v2各走原Prompt/legacy验证；未知/None/缺失版本外发前interrupted/runtime_internal_error且不输出不可信版本。v3只接受JSON alias `fragmentId`等，不接受`fragment_id`或模型位置/原quote；public仍还原exact `{source,quote}`，原计数中的numeric `sourceQuote`保持。
- v3 final只用validate_plain_text验证，不采用其strip返回值，保留冻结稿合法边缘空白；legacy仍保持旧strip行为。逐span→完整原稿结构/变化行格事实→全部合格相交剔除→最终整稿及行格复核已实现。原费用/claim/revision/source/cancel与PDF双get等边界由隔离PG/API证据验证，完成/零有效和原Word/PDF均有真实本地文件，不把HTTP替身称为生产账号端到端。

## 场景映射（本地合并终核已完成，QA另列）

| 场景 | 必需证据 | 当前状态 |
| --- | --- | --- |
| A1 deterministic complete partition | 新anchors回归覆盖边界/ID/span/原序join，338组通过 | 合并686与独立证据通过 |
| A2 repeated text distinct positions | v3双重复600片只改指定位置，legacy count拒绝；独立eval/PG补不同位置 | 合并686与独立证据通过 |
| A3 whitespace and Unicode | CRLF/孤CR/LF/tab/空行/组合字/边缘与末尾保留，338与独立PG同稿检查 | 合并686与独立证据通过 |
| A4 maximum budget | 40000+12000、短行/UTF-8/转义、<=260/32KiB原预算回归 | 合并686与独立证据通过 |
| A5 invalid evidence | 未知/错源/伪ID/offset/额外字段及alias负例，固定全局失败 | 合并686与独立证据通过 |
| A6 exact public quote | eval逐public字段/精确quote及roleMatch双来源；独立HTTP两份wire无内部字段 | 合并686与独立证据通过 |
| A7 factual guard | 原事实AST与259旧例保持，新增v3/72eval正反事实检查 | 合并686与独立证据通过 |
| A8 duplicate qualified IDs | 同span合格候选全overlap/顺序/noop与坏edit隔离回归 | 合并686与独立证据通过 |
| A9 partial and zero edit | 未知/JD edit旧组与首原因；真实PG免费/积分partial/六类失败原路一次释放 | 合并686与独立证据通过 |
| A10 strict global/no-effective | 全局/schema/语言/评分/JD/最终稿与empty/noop/首原因，eval和PG通过 | 合并686与独立证据通过 |
| A11 actual isolated PG/API | 33新PG与22旧safe/62旧service，重放/取消/源删/旧claim/修订和唯一扣退/no-store | 合并686与独立证据通过 |
| A12 version/export compatibility | 默认/新任务v3，旧v1/v2/unknown0HTTP；真实商务PDF/原Word/事实确认/第二次revision/source门禁 | 合并686与独立证据通过 |
| A13 injection/transport/privacy | 注入/伪表/额外字段/重复key/BOM/围栏/非stop和安全异常，旧传输回归保持 | 合并686与独立证据通过 |
| A14 bounded optional quality | 固定37a6/f2c981/11cc047/五源/六case各1请求，6started+6result/0重试；5有安全实质稿，第6例固定责任原因失败，verify拒绝 | 执行/次数边界核对完成，真实质量未全通过，Q1未解决 |
| A15 QA prerequisites | 准备GO、实际37a6禁网/234/202/340/真实导出/七副作用0、Linux单root挂载和独立候选/调用GO；每例受已审控制器的基线/完整七gate/marker门槛约束，保留最后case6七gate明细均exit0 | 前提和失败停止行为核对完成；早先逐例gate明细被覆盖未单独保留，不冒称6套原始快照 |
| A16 complete-source Markdown preservation | 块断头/CRLF中间、对应行ending/缩进/前缀、标题/分隔/空白/pipe/cell边缘与正常格内改写 | 合并686与独立证据通过 |
| A17 line/cell fact ownership | 整块计数不变却跨行/格搬技术/数字/技能被拒，最终合并整体及行格复核 | 合并686与独立证据通过 |

## 实际命令、独立审查与质量边界

独立首轮eval runner有16项assert失败，原因是隐私visitor误把原summary四计数中的numeric `sourceQuote`当成模型原引文。只修测试visitor允许精确四count对象和StrictInt，仍拒绝fragment/offset等内部字段，没有因此改产品。第一轮隔离PG29/29通过后再加4项JD/legacy重复/修订独立例，最终该组33项；旧阶段结果保留，不冒称首次即完整190项通过。

本地review另发现v3继承的WireModel可能接受Python字段名；最终独立v3 schema显式只接受alias，`fragment_id`/额外字段/非字符串ID回归拒绝，未修改原public/legacy WireModel或放宽结构。已绑定最终schema SHA，不把收紧修正写成线上失败。

6份独立合成质量材料已准备于`quality-cases/`，manifest SHA`3e92ef7eb6a4c42e16e8baea8ebb278198a5dce0a1896df88409c6d7ce5b9db1`；normalize后resume为2995/3251/3205/3077/3797/2919字符，3无JD/3有JD，覆盖校园、重复句/段、72CRLF/空行/quote/list、允许HTML表格及JD、672字符中英长行、非技术运营。`quality-case-preparation.json`仅证明保存文件SHA及原normalizer逐字核对（normalizer6c61…与fresh231一致），**不是真实质量验收**。材料准备阶段没有模型/SSH/用户资料或生产测试写入；后续root仅隔离QA准备动作另列，不能把其准备GO当模型调用GO。

## 实际QA工具与隔离候选准备（准备快照0请求，正式QA另记）

`qa/local-final-input-check.json`确认39冻结文件/SHA及6case绑定；controller SHA`f2c981550272ab4f80f0b42f5813219febe8a3522f3cebf260689b3838791b4e`、plan SHA`11cc0479b6e676edac1d9a3f7f6a679b5493615ce99dc2e10c4a6834b91d1cdf`。`qa/independent-final-QA-tools-review.json` SHA`b15e87ad81e951e4b01217a45b7666ec20a1184bb359fa13a6805c36c6da66c7`独立审查通过/无未决发现，实际最终26/26纯/MockTransport工具测试通过，覆盖固定父digest/旧七gate与candidate分离、单root只读挂载、持久排他marker与单次外发/失败停止及隐私边界。该26项不计入686，也不是实际模型质量或当时尚未构建的候选证明。

`qa/root-qa-preparation-go.json`只批准隔离候选准备、明确modelCallsAuthorized=false和productionSwitchesAuthorized=false；root在`/opt/offersteady/qa/20261019-cn-resume-anchors-1`实际initialize成功、upload39项SHA核对成功，均记录模型0/生产切换0。没有权限绕过活动/质量门禁或部署。

`qa/actual-prepare.json`和`qa/actual-prepared-evidence.json`真实候选`sha256:37a6b2308ce48b5a88dd7141e2cf3f56318db4dde028b2185766cb079cdcd5e5`的禁网只读先验通过：234完整运行输入、202完整schema/无新增路径、340Settings按固定探针验证，真实anchored验证通过；10份已验收商务PDF各源SHA/PDF字节SHA/页数完全相同，共14页，真实原DOCX及service默认/注入、facts/owner/revision和双get等守卫通过。网络/数据库/文件写/线程/子进程/依赖/lifespan七类计数和业务/计费写均0，未进入业务lifespan。实际Linux单root只读bind挂载演练通过，读取预建的0600合成case1，SHA与已冻结371f3336…相同，2995字符；不把本机演练替代此实际证明。

截至actual-prepare与独立候选审查快照，真实模型0请求、无case marker/结果。随后`qa/independent-actual-candidate-review.json` SHA`5bfdbcff2f032ecb24ded022381870b2a0e4649b7d7951e477927d2c5bc68d37`审查实际候选/固定父Config和RootFS前缀、完整234/202/340/315/7非目标等通过；该审查是独立读实际root回执及冻结实现，并未重复SSH或运行候选。`qa/root-real-model-qa-go.json` atMs1792346361833另行批准固定37a6/f2c981/11cc047及6个固定case各至多1次，总<=6，仍要求每例实时完整七门禁且失败/未知停后例。该0请求为准备快照，不能用作执行后的当前总数；截至该准备阶段4.1/4.2尚未完成，最终执行收尾见下节。QA调用成功也不等于生产已更新；真实用户资料、生产job/usage/钱包/资料、Global/助手/Git仍不涉及。

## 真实纯合成质量阶段（已结束，5成功1失败）

`qa/actual-case1.json`至`actual-case6.json`绑定固定37a6候选、11cc047计划、原父6f9、相同五运行源/Prompt及固定probe/case，均requestCount=1/attemptConsumed=true；1–5为passed=true/actualSafeRewrite=true，第6例passed=false/summary=null。`qa/actual-final-evidence.json` SHA`6b1f2cb2066514ecc6ae7746752a5416ea33814d67e16fbe9fbc6029b2e73b88`保存6started+6result，exitCode为0/0/0/0/0/1，总实际请求6、无未知/重试，6次授权预算全部消费。全部为直接Provider质量请求，没有创建业务job/usage/钱包/资料。

| case | 结构 | 请求 | 耗时ms | 提议/采用 | 未采用 |
| --- | --- | --- | --- | --- | --- |
| 1 | 校园 | 1 | 19563 | 3 / 3 | 0 |
| 2 | 重复职责/段落 | 1 | 18695 | 4 / 4 | 0 |
| 3 | CRLF/引用/列表及JD | 1 | 26799 | 5 / 1 | 4项factCheck；其余组0 |
| 4 | normalize表格/JD | 1 | 26199 | 5 / 5 | 0 |
| 5 | 中英技术长行/JD | 1 | 24650 | 3 / 3 | 0 |
| 6 | 非技术运营 | 1 | 21397 | 未知，无summary | invalid_output / facts / fact_responsibility_changed，未交付稿 |

前5例sourceQuote拒绝计数均0，合计20提议/16采用/4未采用；该计数只覆盖成功5例，不能推断第6例提议/采用数。第三例4项factCheck未采用并非整份失败，它有1项合规实质修改；factCheck是宽计数组，还含结构/plain-format拒绝，不能称4项都在编造事实。没有保存或读取原模型响应，无法确认第6例哪条edit、触发词、fragment/line/cell/final-merge层，亦不能断言全部edit无效或已确定是误拦。小样本不换算生产成功率，不复现或证明修好了历史真人稿。

`qa/actual-verify.json`实际passed=false、reason=prior_case_not_successful（exit1），正确阻止将失败run当作质量验收通过。随后`qa/actual-post-qa-probe.json`独立action=probe通过，重新确认234/202/340/10PDF同字节/真实Word/双get及七副作用0；冻结probe action前后也核对原Backend6f9、7非目标/Web315/NGINX/Settings/完整schema保持。这个通过只证明安全/基线完整，**不能覆盖verify拒绝或质量失败**。没有发布/重启生产组件、业务写入或Git。

每例case回执依赖已审冻结控制器在外发前完成最新基线、实际offline/mount及完整七门禁并持久消费marker。导出的详细gate仅最后case6快照，七项exit0且保护计数全零；其中旧failed queued信息计数7是既有非保护说明，不虚称所有信息字段都为0。早先逐例详细快照被覆盖，未单独保留；成功回执/固定控制器路径证明其执行前提，不冒领6套明细。失败后未续调/换模型/换目录/清marker，0剩余额度。

`qa/independent-final-quality-review.json` SHA`64cdfe133e31879969060efd37728859ad52205f18a26f38c17b30e544c9cae7`审查已完成、evidenceIntegrityPassed=true，但passed=false/qualityEvaluationPassed=false/releaseRecommended=false，保留1项未解决质量发现Q1（第6例未交付）。这是证据审查完成而非质量通过，也不是第二次SSH/模型执行；root已读并认可，不部署当前候选。

`root-quality-disposition.json` SHA`70fc9b640cb31270400ada9c835772aee744e173650d1c5373b3b22236c9598b`记root独立逐一核对6个marker/result/action/每例1请求/计划/候选/源/退出码：evidenceAccountingPassed=true，但realQualityAcceptancePassed=false、readyForDeployment=false、openQualityFindings=1、remainingAuthorizedRequests=0，原服务保持。此为最终处置依据，不将任务7/7写成质量成功。

纯本地`qa/provider-responsibility-boundary-analysis.json` SHA`f7b27ae411047dda8a36daaff0e4dacbfba61a8c5d73c87e4e51f55a70a5c197`及独立构造说明：旧责任词substring规则可将“其他参与者”之类称谓替换判作责任变化；同一本地合成示例可在行级触发而片段检查通过。这是无模型/无用户数据的另造边界，**不是actual case6响应或根因证据**，不能据此猜实际失败句、层或全部提议。冻结五源/guard未改。

下一步需专门处理责任语义误判风险与生成约束，保持真正责任升级拒绝并补正负回归后另行评审；本轮不放宽守卫、不修改冻结候选/Prompt，不授权新的真实调用或以新目录绕过已消费6预算。当前只交付本地实现及真实失败记录，候选不得发布。

纯eval/假transport、隔离PG、实际禁网候选和真实Provider分开记述；失败回执及已消费marker保留，不能重跑采样掩盖。[本地记录](../../../docs/releases/cn-resume-optimizer-anchors-local-20261019.1.md)交付完整代码/686自测与6实际请求结果，7/7是任务执行收尾，非质量成功。双根strict/链接最终记录另据实际执行填写，root仍会独立复核并留final-validation；真实质量Q1继续未解决、不得发布。

没有真实用户材料/Prompt/响应进入夹具或本地报告，不输出密钥/私有配置/用户标识/原日志；记录只含合成case标识、固定结果/原因/计数/时长与实际请求数。局部静态事实检查和少数合成请求不能证明全部语义、历史用户问题或长期质量。

root本地实施GO、冻结实现、合并终核和真实QA执行/记录已完成；本轮真实质量未全通过，Q1未解决，原线上服务保持。任务完成不能被解释为质量GO、上线或所有用户简历已解决。

文档收尾：双根strict均exit0、change与本地记录的Markdown文件链接存在且两根同文，实际检查写入`local/spec-docs-final-check.json`；root会再独立检查并写final-validation，任何文档校验通过均不改变质量未通过/不得发布的处置。
