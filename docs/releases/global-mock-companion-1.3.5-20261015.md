# 国际服模拟面试优化与助手 1.3.5 — 2026-10-15

用户授权测试通过后同步国际服性能、收音及稳定性优化，并明确保留国际服现有收费。本记录对应 [OpenSpec 变更](../../openspec/changes/sync-global-mock-and-companion-1-3-5/proposal.md)、[模拟面试可靠性规范](../../openspec/changes/sync-global-mock-and-companion-1-3-5/specs/global-mock-turn-reliability/spec.md)及[三平台发布规范](../../openspec/changes/sync-global-mock-and-companion-1-3-5/specs/global-companion-1-3-5-publication/spec.md)。

**当前状态：2026-10-15 06:33:29（Asia/Shanghai）完成国际服 Backend/Web 切换，三平台 1.3.5 公开下载及网页验收全部通过。** 国际服原收费、模型、语言和功能开关保留；没有更新国服。

## 已确认的范围

- 提交回答后撤销旧轮收音，再开始下一题；慢 ASR 关闭由独立的 4 个线程跟踪，活动与关闭中的采集仍受原有 64 路上限约束。取消观察任务不能丢失实际关闭工作，迟到音频或转写不能进入新轮。
- 麦克风 WebSocket 断连清理兼容已断开的连接，不能移除替代连接。生成诊断仅记录固定阶段、耗时、允许的错误类别/HTTP 状态及随机诊断 ID，不记录简历、问答正文、供应商响应或原始异常文本。
- 国际服助手使用英文界面和权限说明、稳定 Global 身份与独立数据目录，生产有效地址为 `https://offersteady.com/app` 和 `https://offersteady.com/api/v1`。实际包内无本地测试配置或服务端凭据。
- Global 保留七天及以上购买套餐的会员准入、UTC 每日三场、无国服积分钱包访问及原有普通面试规则；不加入国服 100 积分收费或 60 分钟截止。既有语言、模型、Prompt、TTS 与 Creem 行为保持。
- 保留已经上线的五字段权威网页 heartbeat、桌面 heartbeat 合并与 P95 请求分类。国服、Global Admin、worker、PostgreSQL 和 Redis 不在本轮切换范围内。
- Global 公开 `/api/v1/mock-interviews/capabilities` 的 `enabled` 在本轮开始时为 **false**，本轮保持原开关。合成测试仅在隔离环境启用模拟面试来验证代码，不代表线上功能已开启。

## 实际组件基线与候选

| 组件 | 本轮开始时实际运行镜像 |
| --- | --- |
| Global Backend | `sha256:54e8e804a8bd8a39ad0adf91d7db414add952153ee8914482dac5b9df8a3a688` |
| Global Web | `sha256:aa40ed431a67f81c36263b9051621cb63371b982fee55d25bc4769c29142c7c5` |

后端源候选仅包含 `modules/mock_interview.py`、`services/mock_interview_audio.py`、`services/mock_interview_diagnostics.py`、`services/mock_interview_generation.py`、`services/mock_interview_jobs.py` 与 `services/mock_interview_runtime.py` 六个文件。独立审计确认其余 155 个原应用文件保持，Global/CN Repository、普通实时通道、配置、Prompt 与模型未被混合工作区覆盖。发布镜像另携带本次 Global 下载清单；回退镜像携带原清单。

Web 已基于实际 `aa40…` 镜像构建冻结候选 `sha256:ab7706981124579a9fb6e703702202c299817af1a78330068637bd7ba6eaca0c`，完整文件 SHA 保护覆盖原 186 个文件至候选 200 个文件；保留旧静态资源、媒体及原 Nginx 路由。旧 future/latest 标签不代表实际运行基线，也未用于本候选。

冻结补丁为 31 个文件、346687 字节，归档 SHA-256 为 `733698911c3c3df750677fb40c52130a11174f4061b99db57ad3445655b70402`。网页增量包含聚合状态请求协调、需要权威结果的强制刷新调用、对应分包引用及三平台 1.3.5 下载元数据；Global 收费、Word、十种语言与 Creem 行为保持。真实 Chrome 在隔离合成 API 环境完成 12 个桌面/移动场景，验证模块实际导入、公开入口延迟加载、身份/缓存隔离、收费/额度页面与报告导出，两个 Word 文件的 ZIP/XML 结构通过。

原 CSP 对 inline JSON-LD 的拒绝在实际基线中也存在；本轮没有更改 CSP，浏览器检查确认没有新增 CSP 拒绝、页面 JavaScript 错误或横向溢出。证据见冻结补丁清单（本地证据：`artifacts/global-mock-companion-20261015/web/patch-manifest.json`）、冻结完整性（本地证据：`artifacts/global-mock-companion-20261015/web/frozen-payload-verification.json`）和隔离浏览器记录（本地证据：`artifacts/global-mock-companion-20261015/web/browser-smoke.json`）。上线后另以匿名 HTTP 完整核验下载及 31 个增量文件的公开字节，没有在生产登录或创建面试。

## 已完成的验证

| 验证 | 已执行结果 |
| --- | --- |
| 实际 Global 后端源候选相关回归 | 261 passed、16 subtests passed、0 failed、0 skipped；1 项既有依赖弃用提示 |
| 其中 Global heartbeat / ACK 专项 | 36 passed、16 subtests passed；已包含在上述后端回归中 |
| Windows 独立源快照 Desktop 测试 | 41 个测试文件，228 passed；类型检查及 Global 编译通过 |
| macOS 独立源快照 Desktop 测试 | 233 passed；类型检查及两个架构编译通过 |
| 三平台正式载荷一致性 | 每包 22 个冻结 dist 文件逐一匹配，两个 Mac 架构及 Windows 共用行为一致 |
| macOS 实际签名、公证与权限 | 两架构 App/DMG 公证 Accepted，Stapler/Gatekeeper 通过；每个 App 16 个 Mach-O 组件检查通过，实际音频输入权限和 Global 英文原生声明通过 |
| Windows 正式载荷 | NSIS 容器与内部 x64 载荷完整性通过，应用 PE machine `0x8664`；安装器及应用证书表均为零，真实状态为 unsigned |
| Global Web 源回归及类型检查 | 29 个测试文件、188 passed；类型检查通过；首页下载元数据另有 9 项回归通过 |
| 冻结 Web 真实 Chrome 与 Word 检查 | 12 个隔离桌面/移动场景通过；两个合成 Word ZIP/XML 结构通过，原 CSP 行为保持、无新增拒绝 |
| Global 发布工具独立保护回归 | 历史版本私有 overlay 修复后主 53 项、独立上传/清单 20 项、独立切换/多 Compose 11 项，合计 84 passed |
| 三平台 OSS 对象完整读回 | 全部 size、SHA-256、MIME 与已验证正式包一致；上传阶段没有更改公开清单 |
| 服务器实际候选只读运行 | 161 个应用文件、74 个 Prompt、151 条 HTTP 路由及模型摘要通过；Global 权益与英文 Prompt 保留，禁止网络/数据库/写文件，没有进入应用生命周期 |
| 公开生产验收 | 三平台 Range 206、整包 200、大小/MIME/SHA 全匹配；31 个增量文件公开 SHA、JS 缓存/MIME、首页/登录/下载/应用入口通过；会员目录及原关闭开关不变 |

后端仅使用本机专用合成 CN/Global 数据库，没有复制生产数据库、使用真实用户内容、创建真实收费记录或调用真实模型/音频供应商。客户端验证包含最终包内编译函数与合成运行环境检查，没有启动正式 Global App；不能将其表述为实际麦克风验收。

本地证据见 后端验证报告（本地证据：`artifacts/global-mock-companion-20261015/backend-verification.json`）、源码保护清单（本地证据：`artifacts/global-mock-companion-20261015/backend-allowlist.json`）、Windows 报告（本地证据：`artifacts/global-companion-1.3.5-20261015/windows/report.json`）和macOS 报告（本地证据：`artifacts/global-companion-1.3.5-20261015/macos/report.json`）。

## 正式安装包与对象读回

| 平台 | 正式文件 | 字节数 | SHA-256 | 分发验证 |
| --- | --- | ---: | --- | --- |
| macOS Apple Silicon | `OfferSteady-Companion-Global-1.3.5-macOS-arm64.dmg` | 124870768 | `4627157d952b01b5d1fd5f3dc37b1324002963a346fdc063db3a8d630fdb8a00` | 已签名、公证、完整 OSS 读回 |
| macOS Intel | `OfferSteady-Companion-Global-1.3.5-macOS-x64.dmg` | 128628212 | `d58f4a021831e672c6ce26abbbbc4081abac867417278a89a088cc369156869d` | 已签名、公证、完整 OSS 读回 |
| Windows x64 | `OfferSteady-Companion-Global-Setup-1.3.5-Windows-x64.exe` | 102214234 | `8274d66bad71124b3fac6dd01f11048a7f460ee984bf9ddc798b66438f0a73e2` | unsigned、NSIS/x64 载荷通过、完整 OSS 读回 |

三平台协议版本为 2.0；Mac 最低 macOS 14.2+，Windows 最低 Windows 10 22H2+。Mac MIME 为 `application/x-apple-diskimage`，Windows 为 `application/vnd.microsoft.portable-executable`。对象位于 `global-desktop-releases/{platform}/{architecture}/1.3.5/{fileName}`，没有更新其他版本对象或 latest 指针。

完整 对象读回证据（本地证据：`artifacts/global-mock-companion-20261015/release-input/objects-readback.json`）与安装包验证证明（本地证据：`artifacts/global-mock-companion-20261015/release-input/installers-verification.json`）均已落地。已生效的新 Global 清单（本地证据：`artifacts/global-mock-companion-20261015/release-input/input/global_desktop_release_manifest.json`） SHA-256 为 `878903ea0a42a256d3dc3b7535f20434724f56ccfd851c7582ea0713302dbbe7`；源码中的 Global 清单也已同步，避免后续重建退回旧版本。

## 切换与回退保护

[Global 发布工具](../../scripts/release_global_mock_companion.py)冻结每个目标组件实际使用的全部 Compose 与环境文件，保留原 project directory、文件顺序、完整渲染配置、源文件/旧静态资源和模型参数。备份、完整容器检查及凭据仅保留在服务器私有发布目录 `/opt/offersteady-global/releases/20261015-global-mock-companion-135-1`。

准备阶段发现原 Compose 渲染的 `OFFERSTEADY_APP_VERSION` 与实际运行 Backend 的历史版本覆盖不一致。冻结配置只增加服务器私有的版本 overlay，保留实际运行版本；原环境文件逐字节不改。原始渲染 SHA 与有效渲染 SHA 分别绑定，overlay 仅能包含该版本字段；其他任何环境差异仍拒绝切换，回退沿用同一实际配置。

新/回退 overlay 使用不可变镜像 ID；专用 Web 回退标签锁定实际 `aa40…` 基线，不使用旧 future 标签。候选 RootFS 层前缀、完整应用文件哈希、真实浏览器验证及网页文件哈希均须匹配。仅在即时受保护用户工作门禁通过后切换获准 Backend/Web，失败回退使用冻结配置并核对完整容器/HostConfig/挂载与旧源码。手工回退先核对输入证明、目标范围及当前镜像仍属于本轮，不能覆盖后续发布。

[安装对象上传工具](../../scripts/upload_global_companion_object.py)只读取已有 Global 服务凭据，上传精确平台对应的版本对象并完整读回，不能修改公开清单；已有大小、哈希或 MIME 不一致的对象不得覆盖。部署过程中不删库、删表、清理用户数据，也没有新增数据库结构或执行额外迁移脚本。

## 生产结果

生产切换完成时间为 2026-10-15 06:33:29（Asia/Shanghai）。Backend 容器 `c87d92ce07300e7e34af617d8fe378f0db55f7b4c83ee492c7f584f4e17d7efc`，Web 容器 `acf077948f491bacb9ba8fc5224fafb4f615d734e3c36e139bf68397647c15c0`。

| 组件 | 已生效镜像 | 固定回退镜像 |
| --- | --- | --- |
| Backend | `sha256:1dab56432de7606b172e30c84033e82fc44a236015c1e21a6ad0826e33be6348` | `sha256:5034d5e901f7327e98d7f652b84fecfe6f855dcc84c30c172c3afb9eb450da06` |
| Web | `sha256:ab7706981124579a9fb6e703702202c299817af1a78330068637bd7ba6eaca0c` | `sha256:aa40ed431a67f81c36263b9051621cb63371b982fee55d25bc4769c29142c7c5` |

预检及切换前两轮即时检查中，原普通面试、模拟面试和补充的租约/生成/资料工作门禁均通过。实际环境、完整配置、挂载、模型和其他五个组件的容器/镜像/启动时间全部保留。候选及回退包已经准备，未在生产执行回退演练。

公开构建标识为 `20261015-global-mock-companion-1`；实际入口 `main-827d17f5.js`，状态适配器 `product-edition-8b060d5f.js`。三个完整安装包均与本地正式产物一致，16 个公开页面使用正式路径核验，新 JS 使用 immutable 缓存且 MIME 正确。118 个旧静态资源均 HEAD 200，旧入口、旧状态适配器与 Word 导出模块完整 SHA 保留。验收脚本最初误用被原路由禁止的 `/index.html` 文件路径，修正为正式页面路径后全部通过；没有为此更改线上路由。Global 会员目录摘要仍为 `3c082fd29ec1f9ea523ee56351f75d02ceb13845f9c9afb6ae99dcefbc41b924`，模拟面试开放开关仍为 false。

上线后 268 秒短观察中 Backend healthy、两目标容器均运行且重启次数为 0；检查 Backend stdout/stderr 没有 ERROR/CRITICAL、Traceback 或 5xx access 行。该检查不代替实机收音或真实负载下的长期 P95 比较。

安全证据：切换结果（本地证据：`artifacts/global-mock-companion-20261015/deployment-proof/deployed.json`）、候选验证（本地证据：`artifacts/global-mock-companion-20261015/deployment-proof/candidate-verification.json`）、后端只读探针（本地证据：`artifacts/global-mock-companion-20261015/deployment-proof/backend-candidate-probe.json`）、公开验收（本地证据：`artifacts/global-mock-companion-20261015/deployment-proof/public-verification.json`）、旧资源兼容（本地证据：`artifacts/global-mock-companion-20261015/deployment-proof/old-assets-public-verification.json`）及短观察（本地证据：`artifacts/global-mock-companion-20261015/deployment-proof/post-deploy-observation.json`）。私有配置和回退材料只在服务器发布目录保存。

生产切换时没有创建新的 Git 提交或发布 tag，也没有覆盖此前已封的国服 1.3.5 tag。研发源码后续归档到 [20261016.1 Git 小版本](release-20261016.1.md)。实际发布依据为冻结源/安装包/镜像和上述逐项证明，不能将共享研发源码直接整包重建为国际服。

## 人工验收限制

没有完成 Windows 实机、Intel Mac 或 Apple Silicon Mac 的真实麦克风/系统音频、权限点击、扬声器回声、耳机、连续换题与暂停恢复验收，也没有替用户授予权限或创建线上练习。正式更新后仍需用户验证实际收音与普通面试体验；Global 模拟面试的实机流程还取决于原有功能开关，本轮保持关闭。Windows 仍未签名，可能出现操作系统安装提示；Mac 的公证/签名检查不能代替实际收音体验。
