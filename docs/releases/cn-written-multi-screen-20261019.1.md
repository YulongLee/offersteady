# 国服笔试多屏回答 20261019.1

封版说明：本文保留开发及发布时的历史状态；当前已部署源码与最终封版以 [cn-20261019.2](../../releases/cn-20261019.2/README.md) 为准。
状态：国服第二轮已成功上线，独立verify、公开多屏策略和180秒脱敏错误观察全部通过；可交由用户实际测试。首轮验收工具错误与保护恢复历史保留如下。

## 范围与继承

基于用户确认的 `release-cn-20261019.1` 开发，并重新核对实际运行基线：Backend `f6dbe8fd498f` / 容器 `db1d63010436`，Web `2124eee82945` / 容器 `88ae70c9fd1b`。完整230运行输入、202接口路径、340配置字段和315网页静态文件与刚封版记录一致。

本功能仅增加笔试顶部默认关闭的“多屏回答”。开启后用网页“截屏”连续采集最多4张画面，支持移除，点击“回答”统一处理一次；只采集不调用模型或扣用户积分，回答沿用现有一次截图回答权益。关闭恢复旧单图。桌面系统全局快捷键仍为旧单图，要累积请使用网页按钮。

Backend只改6个截图相关源文件，其他224输入保持；原202路径不变，仅增加一个批答路径和3个schema的兼容字段。Web增加13个hash资源，只在4个HTML入口改模块URL；其他旧文件字节保留，候选328文件。原单图方法保留，普通面试继续运行原生产LivePage；模拟面试、简历v2改写与旧PDF、会员规则和性能补丁保持。配置、依赖、数据库、模型配置、NGINX及6个非目标容器不变。

## 首轮固定候选和保护

- Backend候选：`sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88`
- Web候选：`sha256:011d1f5de69f1208bf8b9c5b9496d4acddcbe090e6c159a0173214eb8efbbee2`
- 独立服务器目录：`/opt/offersteady/releases/20261019-cn-written-multi-screen-1`
- 控制器SHA：`1f7d78116cb56ceabce07331ace2153723cc6e62d784099fd22d805fe54e7638`
- 输入SHA：`90d2aeddc8b96bce2fd50e8add33ffe41ac9f10d00796cb0a04744e44513c3de`

37文件冻结并经服务器逐项校验。原完整Config/HostConfig/Mounts/网络与私有环境仅在服务器冻结，主控制器7个独立用户工作门禁和实际TCP/PID/netns保护逐次执行；有活跃或未知状态不切换、不清理、不放宽门禁。回退同样要求归属和空闲证明，只恢复本轮固定旧镜像，不回滚用户资料、任务或账本。主发布控制器及离线探针不调用提供方，独立有界QA另计一次。

## 已完成验证与边界

本地598项Web、32项新增后端回归、类型检查及构建通过；后端扩展回归的旧问题和耗时波动见[本地记录](cn-written-multi-screen-local-20261019.md)，不把它称为同次全部通过。

106项发布保护工具测试通过，15项实际编译Web检查及实际bundle合成浏览器验收通过。实际候选镜像禁网只读24项完整ASGI检查通过：单图兼容、顺序多图、一次任务/一次15积分结算（隔离内存账本）、重复/权限/过期/取消、流式事件、完整源码/schema/Settings核对，所有外部副作用计数0。Web18项新文件/NGINX读取权限通过。

一次独立有界真实视觉联调已执行：两张仅含随机数字的RAM合成图，实际网关同message发送、跨页相加正确，1个HTTP请求、0重试、682ms、1303 tokens（5输出），128输出上限、60秒期限；无业务服务/DB/OSS/会话/用户钱包写入，未保存图片或原始响应。不能将此称为真实Windows/macOS桌面截图已验收，部署后由用户实际试用。

临时图仍沿用当前单Backend进程短期内存，未来多worker/多实例需要先解决图像可读性。没有Git提交/推送、助手分发或国际服操作。

证据保存在主仓库 `artifacts/cn-written-multi-screen-20261019-release/`：新鲜基线、完整payload SHA、实际prepare/离线probe、一次QA、Web审核、门禁及后续切换/verify/聚合观察。私有环境和原始日志不导出。

## 首轮保护恢复与验收修正

首轮新镜像切换后，验收器把 `guide.html/index.html/privacy.html/terms.html` 直接作为公开URL访问。生产NGINX本来只开放 `/guide`、`/login`或`/`、`/privacy`、`/terms`；四个内部文件路径返回404，检查器因此报 `public_route_unavailable`。这是发布脚本的映射遗漏，业务候选和文件未发现异常，不放宽NGINX。

原控制器实际执行了受保护恢复，收据 `restored=true`；只读复核原230源/202路径/340配置/315静态和6非目标保持，Backend healthy/restart0，公开正确映射均200且SHA等于原静态，四个内部路径均404。恢复后的Backend容器 `4d3653af6000dd031e6f090e1dbc2e50b22839d2cc0b2c39f6301335949210b2`，Web容器 `11f545c3b82e42b27c4467b71f3d1982006b6ab97280bae5527047927b8b0c97`；镜像仍为原f6dbe/2124。

原发布目录和所有证据保持，不在已恢复目录重试。第二轮使用 `/opt/offersteady/releases/20261019-cn-written-multi-screen-2` 和对应本地 `artifacts/cn-written-multi-screen-20261019-release-r2/`，重新绑定恢复后的实际归属。仅修验收公开路径映射和脱敏失败定位，保留全部门禁与最终完整200/SHA要求，补404与正确映射回归。六源码及17网页增量保持，一次模型QA仅在候选内容及Settings完全等值时复用，不重复请求提供方。

## 第二轮准备核对（切换前记录）

第二轮在独立目录重新冻结38个发布输入，包含只读公开路径诊断摘要；以下SHA已与实际冻结文件及 `root-payload-verification.json` 逐项核对：

- 服务器目录：`/opt/offersteady/releases/20261019-cn-written-multi-screen-2`
- 控制器SHA-256：`e4f4c50f427e9c43ff91c0cf83beb22680e0fc8c6c1ebc8a4124287bfa6458ab`
- 输入SHA-256：`a1e0d1efe2eaef006eb6f15b16181ba20fd4fd1c09af9013767dd6f2f27d5b99`
- 授权摘要SHA-256：`a7fd15c5d157ac65f00606cf2daf7dc721b27ec0f55fdfd9a9b0e120704fbcbb`
- 恢复后基线SHA-256：`078084d37b8e909ec608f23f9dd7bb4e4bcfa18af3efaf22927b4dd2b001704f`

新鲜基线绑定首轮恢复后的Backend容器 `4d3653af6000dd031e6f090e1dbc2e50b22839d2cc0b2c39f6301335949210b2`、Web容器 `11f545c3b82e42b27c4467b71f3d1982006b6ab97280bae5527047927b8b0c97`；原固定镜像仍为f6dbe/2124。首轮原始db1d/88ae容器记录只表示首轮起点，不能用来替代第二轮实际归属。

第二轮只修正发布验收工具：`index.html` → `/login`、`guide.html` → `/guide`、`privacy.html` → `/privacy`、`terms.html` → `/terms`；13个hash资源仍按原路径直接验证200和完整SHA，不把404作为可接受的成功结果，也不开放内部HTML路径。失败定位只保存安全的公开路径及状态，不输出响应体、凭据或用户内容。

26项公开映射回归通过；136项完整发布保护回归通过，均为0失败/错误/跳过（后者包含映射用例，不把两组相加声称为162个独立用例）。对应证据为第二轮目录中的 `public-checks-fixed-tests.xml`、`controller-tests.xml`、`controller-root-review.json` 和 `root-payload-verification.json`。

六份Backend业务输入、17份Web增量和离线探针与首轮逐字一致；预计仍为230运行输入、203路径、340配置字段及328静态文件。上述是已验证的候选契约，不代表第二轮线上最终状态。独立有界模型QA不重跑；仅在实际候选源码和有效Settings等值核对通过后复用首轮记录。

本节记录第二轮切换前的准备事实；实际切换回执见下一节。最终独立verify和短时脱敏观察仍由主发布任务取得真实收据后补充，首轮保护恢复记录不变。

## 第二轮实际切换回执

`artifacts/cn-written-multi-screen-20261019-release-r2/actual-deploy.json` 记录 `deployed=true`，收据时间 `1792362979156`，对应北京时间2026年10月19日06:36:19.156。实际切换身份如下：

- Backend容器：`d12beb7086a7ab6b51b31ea55236b4891a8663607a174c996659c7a8c253ddd3`
- Backend镜像：`sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88`
- Web容器：`75986fa2193dca8ef72a35efbd5b7d74dde71767a97a3e1a0b09076857ce5310`
- Web镜像：`sha256:011d1f5de69f1208bf8b9c5b9496d4acddcbe090e6c159a0173214eb8efbbee2`

26项公开检查全部为 `state=passed`，包括健康、原功能入口、匿名简历私有接口保护、13个新增资源和四份HTML的正确公开路径映射，最终状态及所需SHA匹配。回执同时确认 `otherContainersUnchanged=true`、`existingConfigurationUnchanged=true`、`optimizerEnabled=true`、`migrationOrDependencyChanges=false`。

实际切换已完成，任务5.4据此勾选；任务5.5的最终独立验收结果见下一节。回执 `components.*.signature` 是创建时冻结的历史身份快照，其中Backend `health=starting` 不代表后续实时健康，不能据此编写当前健康结论。本阶段不声称Windows/macOS真实桌面或长期效果已经验收。

## 最终独立验收完成

第二轮发布成功，`actual-verify.json` 确认完整230运行输入、203接口路径、340有效配置字段、328网页静态文件及6个非目标容器保持预期，26项公开检查再次全部通过。`public-capture-policy.json` 确认公开策略接口200、`supportsCaptureOnly=true`、`maxImagesPerTask=4`，未创建业务工作或调用模型。

`short-observation.json` 记录北京时间2026年10月19日06:36:41.877至06:39:41.877的180秒聚合窗口：Backend healthy、两个组件running、restartCount均0，Backend340行/Web160行日志均未达4000行上限，ERROR、traceback、HTTP5xx均0。原始用户日志没有导出。这是短时发布验收，不代表长期P95或真实Windows/macOS桌面已经验证。

任务5.4和5.5均已完成。可在国服实际笔试页开启“多屏回答”，用网页按钮连续截屏（最多4张）后点击“回答”；本地5180仍是合成演示，桌面全局快捷键继续旧单图。一次有界模型QA通过候选镜像完全相同和Settings完全相同证明复用，第二轮没有再次调用模型。Git、国际服及助手分发均未操作。
