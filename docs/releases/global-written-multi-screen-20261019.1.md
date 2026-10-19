# 国际服笔试多屏回答 — 20261019.1

状态：国际服Backend和Web已上线，独立verify、公开策略和180秒脱敏观察全部通过。用户已明确授权同步今天国服笔试多屏功能并在自测通过后上线国际服。

## 继承与边界

实际运行基线已新鲜只读核对：Backend `sha256:991cabbc65ddec642f1790370b0977f75e5c40e92581ff632de012f960120135`、容器 `39f5e0e8e8fb90ab6ab6ded373e5aa0fd533f577acd709b5739102fc24f2d0fa`；Web `sha256:5b22cd0be64274937c15d51174a25b0063de8af272d848c0c80c3460952648f4`、容器 `004acda71885655cb5be011cff7a80e7bbabfee5ccba1bdb702acc191a903633`。Backend healthy/restart0，302运行文件、222路径、379有效配置字段、217静态文件与上次已发布内容一致，五个非目标组件及共享标签保持。源码和公开静态均以实际新鲜SHA完整本地恢复，私有配置留服务器。

功能仅增加英文笔试默认关闭的Multi-screen answers，可连续Capture最多4张、有序移除并Answer统一回答。采集不调用模型/不占权益，批答按现有一次截图回答Global权益结算；保留paid/free区别及原written入口准入，不引入国服积分。普通/模拟面试、简历每日1次、Global Commerce/Creem、语言/Prompt、鉴权/预取/性能、Admin/worker、数据库、配置、依赖及助手均保留。桌面全局快捷键继续原单图，多屏用网页按钮。

## 本地验证（实际分批结果）

Backend新增/区域40项与既有适用49项共89项通过、0失败/跳过；仅6截图文件变化，其余296输入和132无关方法保持。Global Gateway、语言/Prompt方法逐AST原样。222旧路径完整相同，新增1批答路径、3schema兼容字段和1新schema。此前夹具假设修正记录保留，不宣称全仓全绿。

根独立合成实际应用探针本地28检查通过：完整输入/schema/有效配置、本地HTTP采集/批答/流式/重试幂等/越权/过期/取消/单图、英文网关参数与任务provenance、真实Global内存Commerce一次权益结算与零国服账本。网络/DB/文件写/线程/子进程/依赖构造/lifespan/真实模型计数全0。4份英文合成eval定义保留图序、跨页约束和取消，不能把契约测试称为真实模型语义质量或实体设备验收。

证据根为 `artifacts/global-written-multi-screen-20261019/`。实际候选镜像探针、Web最终测试、发布保护/实际preflight、deploy、verify和180秒脱敏观察完成后再据真实回执补充。无Git提交/推送，国服保持本轮已上线版本。

相关[需求](../../openspec/changes/sync-global-written-multi-screen/proposal.md)、[设计](../../openspec/changes/sync-global-written-multi-screen/design.md)及[任务](../../openspec/changes/sync-global-written-multi-screen/tasks.md)。

## 最终冻结的开发产物

英文Web实际编译17检查、最终bundle浏览器9场景和完整源码类型检查通过，控制台错误0；包括默认off、图序/一次Answer、4图上限、移除/关闭释放、恢复旧单图和普通Global页面。原217静态文件保留，16HTML仅模块URL变化，18新增hash资源，候选235文件；34增量文件已冻结。原正常LivePage、旧单图方法、Global英文Prompt和商业模块保留。新入口 `main-08d5d48b.js`，written组件 `WrittenMultiScreen-532fb063.js`。独立类型/静态/浏览器证据由精确manifest SHA绑定，test harness不随部署发布。

发布控制器201项回归通过，0失败/跳过，Global原六门禁保持原字节，新增实际Global财务聚合与Backend TCP/PID/netns保护。源码/完整Config/HostConfig/挂载/网络、共享标签、非目标身份、断流认领和受保护恢复保留。畸形财务元数据明确停止诊断，不能视为普通活跃延期。

55文件发布输入已本地冻结：控制器 `05a6ddbadde5417ebcb721384b671c6808e77b83917e4ea62c026293ab4e13e5`，input `4f9726f60df68392d0f4d201e9fa8b33eeb5d56af1ecc36173e20b06e3db8ded`，授权 `2708a4302c0b56daafbdb882d533ba341de37cd488f9c703cbbbeff2757ac387`。服务器目标目录 `/opt/offersteady-global/releases/20261019-global-written-multi-screen-1`，当前仅准备阶段，尚未作为切换或最终成功证据。

## 首轮prepare停止及校验工具修正

首轮只执行prepare，未生成prepared收据、未切换任何运行容器。探针误将国服Nginx配置644假设用于国际服；实际旧Global镜像和候选均继承配置模式664、root:root，nginx用户101可读。34份新静态均644且nginx可读，父目录755，配置字节SHA保持。证据为 `release/public-permission-diagnosis.json`；属于校验工具的区域假设遗漏，没有为发布改Nginx或放宽新静态权限。

首轮目录和失败记录保留并禁止继续部署。第二轮使用独立服务器目录 `/opt/offersteady-global/releases/20261019-global-written-multi-screen-2` 与本地 `release-r2/`；新静态仍要求644且实际nginx可读，原配置要求模式/owner/字节与实际基线精确相同。业务6源码、34Web增量和合成探针不变，所有用户保护门禁与最终完整内容检查保持，修正回归通过后再准备实际候选。

第二轮冻结55文件，控制器SHA `c8f59f018ea8ee38b36ddcc78df36060b494df937f2757109ae1c0d13df54356`，inputSHA `3adb5379ea9110d5d352b43eef76ba4ed3c73407c25a028af4ba403054d57cf2`，授权SHA `87ec501c8320b40d0a3aa66bef2ae640c67073f70582be1b2dad6906c557d634`。221项完整控制器回归通过，第一轮到第二轮仅有基线权限元数据绑定、独立tag/目录和公开权限探针三个函数变化。首轮与第二轮源码、静态、完整API及合成探针逐字节等值，证据 `release-r2/revision2-scope-review.json`。最终准备/切换结果以下续实际收据为准。

## 第二轮prepare的API元数据夹具修正

第二轮公开权限34项和原配置664/SHA/owner实际探针通过；随后禁网Backend探针因预期OpenAPI标题仍为默认 `OfferSteady Backend` 而停止，实际原国际服标题为 `OfferSteady Global Backend`。只改本地验收生成器，继承完整Info、其他顶层及非schema组件元数据；10项定点回归通过，89业务测试绑定及6源码/34静态/探针代码保持。第二轮没有切换运行组件，原收据和冻结包保留。

第三轮目录 `/opt/offersteady-global/releases/20261019-global-written-multi-screen-3`，55文件冻结；控制器SHA `0952ba06e78fe629762461545555368a55c48a8d9e15744386e319c4f6a7f4f3`、inputSHA `cb0a33760816f3bcdc1f7e6d4c21499fc05808d4ccfa185afffb615f8fbc8d6a`、授权SHA `72cd64b62eba070e670ef96bc4dfac33b03a2391fdf9f9df001c469c6bdbb9e8`。第三轮与第二轮控制器只改独立tags/目录，预期完整API只改为正确的原Global名称；生产应用名/版本/有效配置不变。`release-r3/revision3-scope-review.json` 及独立后端审阅保存等值证明。

## 第三轮实际切换与独立复核

北京时间2026年10月19日07:39:10.267（`1792366750267`）取得 `deployed=true`；随后07:39:47.001独立verify通过，43项公开检查全部通过。实际身份：

- Backend容器：`a3a419d5586a1a5e802616ada6efbf59ddc254f0c2724a102e230671d4e61821`
- Backend镜像：`sha256:f6a4dad4fb27222ca79f1fb5a86c23267093c741b4536c64ca76b83ac096ec19`
- Web容器：`6e4bd43d80c1d7f5b5959c3455fc423ca07efd304ef4210a02f2b0b16aa0629d`
- Web镜像：`sha256:7f5fd6640aaea0b742eddb6227c41ddb7a0a0390fbe657486fdfef86efd38ad6`

实际prepare完成28项禁网合成检查：302源/223路径/379Settings完整匹配，外部副作用计数全0；34份新静态及原配置模式664/owner/内容均通过。真实候选完整配置摘要 `3c1d86d84114756dd0d9f51e446765fb56d1e0be00199ee10786d32c9386de07` 保持原值。

新鲜preflight及紧邻切换的七组用户/财务门禁与实际TCP保护通过；没有结束会话或清理活动。部署回执确认 `otherContainersUnchanged=true`、`existingConfigurationUnchanged=true`。独立verify再确认完整源码/静态/API/原配置/非目标身份、43项公开入口/资源/匿名简历401/no-store；公开截图策略200、`supportsCaptureOnly=true`、`maxImagesPerTask=4`。收据在 `release-r3/actual-deploy.json`、`actual-verify.json`、`public-capture-policy.json`。180秒短时观察完成后补最终结论，不把创建时signature的starting当作当前健康状态。

## 最终观察与交付完成

北京时间2026年10月19日07:40:00.479至07:43:00.479的180秒观察完成：Backend healthy，Backend/Web均running、restart0，ERROR/CRITICAL/FATAL、Traceback、HTTP5xx（含结构化状态）均0。Backend22行、Web2行，未达4000行上限，没有导出原始用户日志。证据 `release-r3/short-observation.json`，仅代表该短窗口，不代表长期P95或模型语义质量。

本轮12项任务全部完成，实际国服服务、国际服Admin/worker/DB/Redis及助手分发未发布，原Global会员/免费权益和收费保持。未调用真实模型或创建生产测试面试，没有Git提交/推送。两次prepare停止均在生产切换前，第一、二轮不可再次部署；第三轮完成一次受保护双组件切换，无生产回退。

用户可在[国际服笔试](https://offersteady.com/app/written-exams)刷新、登录原账户，开启Multi-screen answers，用网页Capture最多4张后Answer统一处理。关闭开关仍为原单图，桌面全局快捷键继续旧单图。真实Windows/macOS捕获与本人体验由用户实际测试。

[当前国际服基线](../current-global-baseline.md)、[恢复说明](../../releases/global-20261019.1/README.md)与[逐场景核对](../../openspec/changes/sync-global-written-multi-screen/verification.md)已保存。恢复包内的pending文档仅是打包时历史快照，最终结果以本节及第三轮真实收据为准。
