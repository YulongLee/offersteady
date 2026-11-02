## Context

用户2026-11-02授权国际服性能优化与助手优化，自测后上线。已确认的Desktop来源是[国服1.3.6正式发布](../../../docs/releases/companion-1.3.6-cn-20261102.md)与[本地r3行为](../../../docs/releases/companion-1.3.6-local-r3-20261101.md)，不是直接分发国服包。Global既有身份/分发及独立收费来源见[1.3.5记录](../../../docs/releases/global-mock-companion-1.3.5-20261015.md)与[国际服部署边界](../../../docs/global-production-deployment.md)。

本工作区以国服封版为基线，不能代表国际服现状。历史Global封版参考为独立Git ref `codex/release-global-20261022-1`；参考仍须与目标组件实际运行镜像、运行可写层清单、全部公开静态字节核对。另工作区的10月17日鉴权状态、10月19日多屏、10月22日模型发布记录仅作清点线索，不能替代新鲜事实。

完整主机容器集合为七个Global服务和既有停止构建容器`zealous_bhaskara`，不是只有七个运行服务。后者完整H签名已只读核对与10月22日冻结的非目标完全相等，9月7日创建并停止，原ID `b26658773fe6a73626510cba0116d31bb3154d1fb554ca521deb254ef21ef57a`、镜像`sha256:414cfd1c18647de7db5857d6cadb64e46d7e8508c837e7d5e639a682800a3e47`、running=false、restart0及配置/挂载/网络摘要均固定。证据`artifacts/global-performance-companion-20261102/legacy-stopped-container-preservation.json`和八条纯签名基线；原七条未变。该容器仅作为第六个非目标保护，不授权任何启停、删除、替换或清理。prepare在目标freeze前检查其完整签名，后续验证持续核对；未知第九容器、缺失名称或任何签名变化均阻止，不放宽原七项用户门禁。

## Goals / Non-Goals

目标：消除经现场清点确认的共享性能差距，保留Global请求/权限/新鲜度语义；提供独立Global1.3.6三平台正式助手；在真实用户工作闲置时以可验证、可恢复的最小增量部署。

非目标：CN覆盖Global、整包源码重建替代实际静态基线、数据库迁移/索引或依赖/协议升级、启用连接池或功能开关、修改Global收费/会员/Creem/模型/Prompt/ASR/TTS/语言/SEO、Admin/worker或国服任何更新、Git提交推送、真实模型/付费面试/用户内容测试、生产压测或保证物理设备全部场景已验收。

## Decisions

1. **两级实施门禁。** Desktop1.3.6的功能范围已明确且用户已授权，状态`apply-ready`，可立即进行Global英文与身份适配、自测和正式构建。Backend/Web先完成只读清点并由主代理审核下方明确清单，现该清单范围`apply-ready`；任何额外文件或行为保持`scopeReviewPending`。清点发现已同步的优化不重复移植。缺失事实不是放宽允许范围的理由，也无需就已授权发布另行请求用户许可。
2. **Global实际组件分开冻结。** 保存Backend/Web各自的固定镜像、容器身份/启动时间/重启数、完整运行输入、有效配置/依赖/API Schema摘要、实际Compose文件与顺序、热清单、原静态图和非目标组件签名。私密原配置仅留服务器，证据只有必要公开字节和摘要。采用目标实际镜像作FROM和明确最小overlay；不以`current`、future/latest标签或另一个组件源码作基线。
3. **性能行为最小移植。** 只将证据确认尚未同步的已有共享鉴权/状态/heartbeat/control读取优化适配到Global原函数和repository；保持权威鉴权、结束/过期、写后失效、强制刷新、租约/TTL与新鲜度界限。正常持续轮询频率不增加，缓存和合并不得跨用户/令牌/场次或掩盖错误。性能收益以合成读写计数/请求合并与时序回归记录，不能把短观察当真实长期P95承诺。
4. **必要截屏配套。** 既有device next读取增加`sessionId`/`requestId`可选参数，保留设备凭证、当前live绑定及owner/session/device/code校验，无参数保持原行为；查询不claim/写入/扣费/调模型。Global Web本轮不移植国服笔试失败/取消或mock/状态代码，只处理下方明确下载元数据和必要资源引用。
5. **Global1.3.6明确范围。** 同步真实权限/晚结果、已有能力登记合并、mock当前音轨/上下文异常与手动重试、有界心跳与恢复、有效笔试短时防应用挂起、有界FIFO截图/去重/取消与跨场旧结果隔离。沿用已批准外观，无新增独立重新检测或额外说明块；隐藏为同一固定尺寸透明可点击Tray，保留应用重新打开/可用快捷键恢复和网页停止/OS提示，不静默自启或绕过权限。Global原收费不由助手决定，必须保持全部模式边界。
6. **Global发布身份和语言。** 版本1.3.6、Electron42.5.0及既有协议保持，使用Global应用/Bundle/数据目录、英文权限说明与生产`offersteady.com` HTTPS地址；不包含国服配置、local-test-runtime、密钥或真实用户数据。检查新增用户可见错误及主/renderer错误转译完整覆盖，不将未翻译中文发给Global用户；原有语言能力不删除。
7. **构建串行且精确核验。** Desktop构建由同一执行者独占共享`dist/native`，每架构先冻结源/dist与native载荷并核验，再构建下一架构。三平台同一批准源与非native行为；Mac各架构使用稳定Global身份和Developer ID完成App/DMG公证、staple、Gatekeeper及实际主/Helper音频权限和包内载荷验证；本地未公证CN包不能改名。WindowsNSIS验证真实x64、内外归档和全部安装文件，保留unsigned，不虚构Authenticode/实机音频验证。
8. **不可变对象和清单。** 仅向`global-desktop-releases/<platform>/<architecture>/1.3.6/<official Global filename>`上传通过验证的包；禁止覆盖已有不同字节，完整流式读回长度/hash/MIME，三包都成功后才能统一公开清单。当前官网和版本门槛来源必须现场确认；非运行来源的latest不顺手更新。清单以同目录旧hash CAS/fsync/rename或固定最小候选发布；不得使未来重建回退旧清单。
9. **用户工作与恢复。** 正式切换前、每次组件切换和任何可能中断服务的恢复前都重复完整只读门禁：真实普通/笔试/模拟面试、活跃准备页、音轨/发布者、未完成回答、资料/简历/其他后台任务及有效账务；未知或读取失败阻止，使用原财务过程锚点，不随候选重启重置。保留TCP/进程和完整归属保护；忙时等待，不结束、清理或放宽真实工作。新/回退使用固定镜像与冻结实际配置，只重建本轮明确目标，保留当前Web资产供旧页面继续使用。SSH回执丢失先读真实镜像/容器/清单归属；已完成则只读验证，不重复重启。源码/配置/镜像/控制器漂移或未知状态停止自动切换；仅明确归属且门禁允许的失败可受控精确恢复。
10. **公开验收和诚实记录。** 比较完整输入、有效配置/Schema、Global会员目录/语言/功能开关、非目标组件、页面及资产字节。三平台真实下载API Range/整包长度/hash/MIME，匿名健康/既有认证保护路由和短时脱敏ERROR/Traceback/HTTP5xx聚合均记录；不打印签名URL或原始用户日志。硬件收音、系统提示点击、真实休眠/网络与完整线上面试限制写明。

## Backend/Web difference review

状态：**本节精确清单于2026-11-02经主代理审核为`apply-ready`**；额外范围仍`scopeReviewPending`。只读实际Backend302项、独立worker267项和Web235文件与Global封版ref完整一致，证据为`artifacts/global-performance-20261102/actual-inventories.before.json`、`components.before.json`及`backend-baseline/`。实际Backend固定镜像`sha256:63f8243bacfc075cd399032ec5ca05f669356cd087b5d57583a9ce08b474e066`，容器`7bc15c77cef86681d068d6157270f87338d0cab9f1b14c8cddf7d11e83ad7536`；Web固定镜像`sha256:7f5fd6640aaea0b742eddb6227c41ddb7a0a0390fbe657486fdfef86efd38ad6`，容器`6e4bd43d80c1d7f5b5959c3455fc423ca07efd304ef4210a02f2b0b16aa0629d`。后续准备及每次切换仍重验，不以此记录替代现场保护。

已经存在、必须保持的行为：Global1.5秒状态成功缓存/请求合并、原heartbeat/ACK、鉴权usedAt/单查询投影、预取、原Global收费/会员与模型1017均不重复迁移；Global已有ASR异步关闭，不移植CN guarded mockRuntime或启用mock开关。状态缓存不因国服策略不同而替换。

Backend允许清单仅如下八文件中的指定节点，均以实际Global文件作基线并保护其余AST/方法；另允许写入通过完整对象验证的`global_desktop_release_manifest.json`发布元数据：

| 文件 | 允许行为/符号 | 必须保持 |
| --- | --- | --- |
| `apps/backend/app/modules/web.py` | `get_web_state`的Global认证入口接入raw资料seed；`_published_desktop_entry`仅Global历史精确文件名查找fallback | 原`usage_billing`、Creem、Global英文/会员聚合及其余路由；current exact条目优先，CN不读取历史 |
| `apps/backend/app/services/document_service.py` | `list_documents`、新增with-records入口及`_list_document_records`/`_document_list_responses`，请求内复用原始资料读取 | 同一权限过滤、响应、Global资料处理/商业行为，不跨请求保存用户资料 |
| `apps/backend/app/services/session_service.py` | `list_sessions`接收同请求seed；新增`get_control_state`轻投影 | 原列表排序/归属/生命周期/计费，无全量会话装配副作用 |
| `apps/backend/app/ports/interview_session.py` | `SessionControlState`及对应读取port | 原接口行为，五字段权威投影 |
| `apps/backend/app/services/interview_session_repository.py` | in-memory `get_control_state` | 与原owner/status/start/activity字段一致，不写入 |
| `apps/backend/app/services/postgres_interview_session_repository.py` | PostgreSQL `get_control_state` | 一次仅取权威五字段，无资料/对话装配或写入 |
| `apps/backend/app/services/realtime_speech_service.py` | 仅`_compute_desktop_pairing_status`的session_state读取改用五字段 | 绑定/owner、期限、状态错误、租约与TTL、Global权益及其余普通/mock音频逻辑 |
| `apps/backend/app/modules/screenshot_answer.py` | 仅既有device next读取增加可选`sessionId`/`requestId` | 严格当前live绑定及owner/session/device/code，旧无参数合同，终态只读；无claim/模型/扣费/数据写入 |

API路径集合保持，Schema只允许既有next操作增加两个可选query参数；Settings、模型/Prompt、依赖、pool状态、数据库Schema、财务/会员与其它方法保持。候选必须有exact-source和合成回归证明；无新模型评测需求，因为AI行为完全不变。

静态兼容补充已由主代理审核：旧活动main/SSG硬编码1.3.5真实下载URL，单纯只保留旧assets会使旧页面查询当前1.3.6清单时404。允许新增`apps/backend/app/global_desktop_release_history.json`，精确保存实际旧1.3.5清单三个公开条目及原Global对象键；`modules/web.py::_published_desktop_entry`在当前精确查找失败后仅Global读取该独立历史文件，历史绝不混入当前public state或版本门槛，损坏/缺失/未知名字及CN保持原404路径。不是将135URL映射136，不写旧OSS对象。当前136清单与此历史JSON为两个批准元数据文件；新Backend完整输入由302增303。兼容回退Backend以实际基线为底，只保留历史lookup helper、历史JSON和新136当前清单，撤销性能/可选query增量；其Schema保持before，Settings全部恒等。Web兼容回退保留全部旧HTML/字节并附加新assets。新/回退都必须验证旧135和新136URL分别返回各自确切已验证版本，不借历史文件扩大Global用户权益。

Web允许清单仅为实际235文件静态图上的正式三平台下载元数据更新：定位当前活动main bundle，精确更新三条目必要的id/version/url/size/hash/signing/notarized/publishedAt字段；仅`index.html`的三条官方fallback下载链接由135更新136。活动依赖反向closure使用新文件名及相应HTML资源引用，保留所有原235字节供旧页面使用；允许活动HTML引用和必要build marker更新，不删除旧inactive main变体，不重建整站。原1.5秒缓存、UI、多语言、SEO、会员/收费、Creem、Nginx/CSP、mock/状态/取消处理均保持。本轮不移植国服Web业务改动。

Backend和Web具体candidate source/static manifest及SHA由执行者在此审核范围内生成并提交独立验证；发现额外依赖或行为差异时暂停扩范围，先补充证据与审核，不静默添加文件。

## Risks / Trade-offs

- [两个工作区/区域源码不同] → 以实际运行输入和独立Global封版核对，逐函数/静态图最小增量，不整文件替换。
- [缓存或写合并改变权限/状态新鲜度] → 结束、过期、撤销、写后失效、跨用户/场次和强制刷新回归，保持原TTL与权威验证。
- [本地全站build改变Global付费或资源图] → 保留完整实际静态基线与所有旧资产，重建仅用于校验，不自动当线上等价包。
- [签名/Apple或OSS外部服务异常] → 失败阶段不切公开清单，不绕过正式校验或覆盖不可变对象。
- [当前仍有用户] → 安装包准备和合成自测可并行，切换等待完整门禁闲置，不结束用户。
- [Docker挂载顺序导致摘要误报] → 只允许能够精确复原原whole配置摘要的完整Mount对象顺序规范化；不忽略字段或重写基线，真实配置变化仍阻止。

## Migration Plan

实际Global清点和差异审核 → 明确最小实现清单并自测 → Global助手三平台正式包/完整读回 → 冻结目标镜像候选/完整配置/Schema/非目标 → 重复所有用户工作与归属门禁 → 只切明确Global目标/统一清单 → 独立真实状态与公开下载/资产验收 → 短时脱敏错误观察及发布记录。国服、Admin/worker/数据卷不切换，无数据库迁移。

## Open Questions

没有待用户再次决定的产品范围。上述Backend/Web清单已由主代理基于实际差异审核，额外范围仍需清点与审核；Global功能开关/会员目录以现场实际值保持，不能把历史文档中的关闭或开放状态当成本轮启用授权。
