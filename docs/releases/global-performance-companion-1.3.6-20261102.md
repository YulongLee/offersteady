# 国际服性能与伴随助手1.3.6：2026-11-02

状态：**北京时间2026-11-02 03:08:11.804完成国际服Backend/Web切换，03:08:43.044完成控制器verify；公开页面与新旧六包下载验收通过。** 未提交或推送Git。

用户授权国际服性能及助手优化、自测后上线。范围见[OpenSpec设计](../../openspec/changes/sync-global-performance-and-companion-1-3-6/design.md)与[完成任务](../../openspec/changes/sync-global-performance-and-companion-1-3-6/tasks.md)。保留Global原时间会员、收费、Creem、模型、语言、功能开关及1.5秒状态成功缓存/合并；不引入国服积分，不启用原来关闭的功能。国服八组件生命周期及助手清单保持。

## 本次变化

- Backend复用同一请求已读取的原始资料快照，减少状态聚合的重复资料读取；合成场景下下游重复读取由6次降至0。配对状态改为五字段轻读，避免为控制状态读取完整资料。该计数不代表线上总请求量或P95同比下降。
- 既有截图device next增加`sessionId`、`requestId`两个可选只读查询，同场次/设备/所有权与取消终态校验加强；无参数旧客户端协议保持，不claim、不扣费、不调模型。未迁移CN mockRuntime或Global Web业务反馈代码。
- 独立Global助手1.3.6同步已验证的真实权限/晚授权、收音资源释放、旧回调隔离、有界心跳及网络/系统恢复、笔试短时防挂起、有界截图队列/去重/超时/取消和跨场旧结果隔离。保持原外观，无新增独立重新检测按钮；隐藏窗口与Dock/任务栏后保留透明可点击托盘位置恢复。保留Global身份、英文权限及错误文案、`offersteady.com`生产地址。
- Web只更新三平台下载元数据及缓存安全资源引用：保留原235路径，218原文件逐字不变，16HTML及build marker改变，新增16JS。当前公开清单仅136三条；独立历史lookup保留旧135三个精确文件及字节，旧缓存页面仍可下载135。

生产增量来自目标实际Global镜像，不从当前国服根源码整文件覆盖。Global原Backend302输入、独立worker267输入、Web235文件与独立Global封版一致；新/兼容回退Backend均303输入，Web均251文件。Python仅八文件指定读路径，另有当前136及历史135清单；无依赖、数据库Schema、连接池、商业或模型配置变更。

## 正式包与验证

| 平台 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| macOS arm64 | 126277431 | `a9cd0121387f5c393b8d6b7d2eb01b6218f6e92b75b044b1b4feeb53fb172356` |
| macOS x64 | 129965286 | `e159a72d638de953bf009f3f8c24aba995dcec8a2d53a5f0340e6825c359a28c` |
| Windows x64 | 102900062 | `f0b84c6fe131c6e7dba18d48da2a7af462e7dba0cc98d8289c17214217075737` |

三平台94份源输入及27份非native运行文件一致。Desktop55文件401测试、类型检查、Global错误回归7项和包工具6项通过。两个Mac架构各16个Mach-O、稳定Global Bundle ID、实际音频权限签名、App/DMG公证、staple、Gatekeeper及DMG真实载荷通过。Windows NSIS外/内层及78安装文件、应用真实x64和证书表检查通过，保持**unsigned**，不宣称Authenticode签名。

最终Backend业务回归204项、0失败/0跳过；4项专用PostgreSQL环境案例未作此轮实测。最终控制器/组装器129项、Web/上传器23项、只读观察工具17项通过。实际候选隔离probe为9项、兼容回退3项，未启动lifespan/worker或调用真实provider/写数据库；Settings379字段保持，完整API223路径仅允许上述两个可选查询参数变化。保留的初轮95项XML有失败/跳过，不作为最终通过证明。

## 实际发布与保护

固定目录：`/opt/offersteady-global/releases/20261102-global-performance-companion-136-1`。每次执行前核对全部12个支持源码及输入SHA；实际prepare/preflight/deploy/verify均exit0。准备冻结27个私有文件，原环境/Compose顺序、镜像Config及RootFS原层前缀、完整新/回退输入均验收；不修改旧shared/latest镜像引用。prepare/probe的原配置与环境仅保存在服务器。

正式切换前、Backend和Web各自切换前重复七项只读工作门禁和TCP证明。最后记录普通/笔试/模拟面试、准备页、音轨/发布者、回答/截图、资料/简历任务及账务保护计数均0，8000端口ESTABLISHED为0；原财务锚点`1792604406734`保持。未终止用户、清理活动或放宽门禁。只重建Backend/Web，未执行Web/Admin代理reload。

完整主机集合为七个Global服务加既有停止构建容器`zealous_bhaskara`。其完整签名已核对与10月22日冻结非目标一致，9月7日创建并停止，固定原ID/image、running=false、restart0和配置/挂载/网络摘要；作为第六个非目标保护，没有启动、删除、替换或清理它。首次容器集合保护拒绝保留为历史证据。随后隔离probe因公开发布文件权限安全阻断，核对CAS和16文件字节未变后只修公开文件root:0644；未放宽隔离能力，私有文件root:0600、目录0700保持。最终独立权限检查为16公开文件、34私有文件和2私有目录通过。这些是发布准备过程保护，不是产品运行故障。

实际部署归属如下，两容器RestartCount均0；Backend healthy，Web运行正常且无配置健康检查。

| 组件 | 实际容器ID | 实际固定镜像 | StartedAt（UTC） |
| --- | --- | --- | --- |
| Backend | `852d46d9a890ddb763f63167e9d4e67eeede06d12fc8a03bf59e88e9e5bd5cfb` | `sha256:c68c315beb7977cc88c4478d8b2464a560cf9a1226056492c9402d330d9a3398` | `2026-11-01T19:07:24.451450975Z` |
| Web | `a164dbd6999dbfbb47969baee68b482fdc6c100a9c3b0d8f6fcadc9a3c2523ba` | `sha256:73c351fbc0502f50989b729174620173c80988292fe6d0d2b4fcf660f29caa44` | `2026-11-01T19:08:04.603972008Z` |

六个非目标完整签名保持，worker267输入及354项Settings逐项/摘要保持；三个Global OSS latest对象逐hash不变，国服八组件ID/镜像/StartedAt/RestartCount及清单不变。已知切换归属与保存的intent/progress核对通过，无额外重复重启。

## 公开验收与观察

新136和旧135三平台共六个精确filename，真实公开下载API均Range206、整包200，MIME、长度和SHA与对应原始包一致。34个规范公开路由及16个新JS的字节hash全部匹配；健康200，Global目录/功能开关保持，匿名state14个顶层字段保持，匿名sessions/mock-interviews仍401，`/openapi.json`及`/index.html`仍404。不能把原Nginx刻意禁止的index文件URL当发布失败。

以北京时间**03:06:36.707–03:09:37.400**为查询窗口，读取本次新Backend62行、新Web138行及未更换worker0行，ERROR/CRITICAL、Traceback、HTTP5xx均0。新容器日志仅覆盖各自创建之后，不包含旧容器切换前日志；180.7秒是查询窗口，不是上线后连续三分钟观察。未导出原日志、配置、用户标识或签名URL。

实体Windows/Intel麦克风、蓝牙、OS权限点击、真实休眠/网络恢复和完整线上面试未由结构/包验证代替；短时未见错误不能代替长期P95或全量硬件验收。没有创建真实测试面试、调用真实模型、执行生产压测或Git操作。

## 精确恢复与未来重建

恢复使用同目录的同一控制器`rollback`，先重验当前input/全部支持源码、完整运行输入、固定镜像/容器归属、原配置和全部fresh工作门禁/TCP；未知、漂移或忙碌状态停止，不结束用户。回执丢失先读真实归属，已部署只verify，不重复重启。本次未执行回滚。

兼容回退Backend固定为`sha256:9fd209582a020315f4f5a7fa50492cb0b6996b018cb40ecb0717db3006799632`，恢复本轮性能/可选查询变更，但保留当前136清单及精确旧135历史lookup；兼容回退Web为`sha256:2ef84b008e1f2f73b14e3a809164992099c45ebfee51c4ef7089ec63193baf19`，保留原235文件全部字节与新16JS。不要直接使用旧Backend302/Web235镜像替代这两个兼容回退，否则下载或缓存页面所需配套可能丢失。

未来recreate须使用发布目录保存的实际冻结Compose/env顺序与明确固定image overlay，或以当前实际镜像为下一轮增量基线；保留当前136清单、历史135 lookup及已发布静态资产。不依赖current、旧latest或当前国服根源码恢复Global。原私有冻结配置、prepared/progress/verified及恢复材料保留服务器，不能进入Git或客户端。

控制器SHA：`835b29c09a19db58bcdd52fff7b9f803b2851fe4e312eb49fb57c040a69c5ece`；input SHA：`d9c7e0336533f1865374c8c9e0049e954029c9d39ee4edbb636aa66d592e7e08`；当前Global清单SHA：`136f43b076a5064db83b1d747c45f3acb9b6d15c9299eeaadeb6a64c02f4d1dc`。

下载：[Windows](https://offersteady.com/api/v1/web/downloads/desktop/OfferSteady-Companion-Global-Setup-1.3.6-Windows-x64.exe)、[Mac Apple Silicon](https://offersteady.com/api/v1/web/downloads/desktop/OfferSteady-Companion-Global-1.3.6-macOS-arm64.dmg)、[Mac Intel](https://offersteady.com/api/v1/web/downloads/desktop/OfferSteady-Companion-Global-1.3.6-macOS-x64.dmg)。安装前完全退出旧助手。

[完成摘要](global-performance-companion-1.3.6-20261102/release-completion.json)、[当前清单](global-performance-companion-1.3.6-20261102/desktop-release-manifest.json)、[实际发布](global-performance-companion-1.3.6-20261102/release-verification.json)、[三平台包](global-performance-companion-1.3.6-20261102/installer-verification.json)、[六包及页面](global-performance-companion-1.3.6-20261102/public-verification.json)、[state/认证边界](global-performance-companion-1.3.6-20261102/public-state-contract-preserved.json)、[非目标/国服/latest保全](global-performance-companion-1.3.6-20261102/preservation.json)、[短时聚合](global-performance-companion-1.3.6-20261102/postflight-observation.json)、[准备保护记录](global-performance-companion-1.3.6-20261102/release-safety-history.json)、[最终独立复核](global-performance-companion-1.3.6-20261102/independent-release-review.json)、[公开证据hash](global-performance-companion-1.3.6-20261102/evidence-manifest.json)。完整本地证据为`artifacts/global-performance-companion-20261102/`，私有配置与原始诊断不在公开证据目录。
