# 国服发布追加授权与边界

用户在本地交付后明确要求：“上线国服吧。我这边测试下”。本授权允许本功能的国服Backend和Web增量发布，不包含国际服、助手升级、Git提交/推送、数据库/依赖/模型/配置改动或真实用户工作操作。

## 实际基线

2026年10月19日新鲜只读核对及前一发布控制器的完整独立验证通过：Backend实际容器 `db1d63010436b4bb38060dbdc885a80db61deab3f4ebd584700fb255693185a6`、镜像 `sha256:f6dbe8fd498f1f965bf8ba611d666e7ea49475ac1a7bf01b547ed79e8c6bbfaa`，230运行输入、202完整API路径、340配置字段；Web实际容器 `88ae70c9fd1bdf39dd5f7b2f15b54266ca058e23b843ced2d24e22ba15eaaf38`、镜像 `sha256:2124eee829453776d6191b669c29a28c06f83a011bb6b8461432fefd1393463d`，315静态文件。完整清单、配置摘要、NGINX及非目标归属在 `artifacts/cn-written-multi-screen-20261019-release/current-baseline.json`，不导出实际私有配置。

部署前若任何基线或控制器/候选/配置漂移，停止自动切换；不能仅以 `current`、旧目录、Git标签或健康版本字符串判定现状。

## 准备与验证

1. 新私有服务器目录 `/opt/offersteady/releases/20261019-cn-written-multi-screen-1`，固定发布控制器/输入/全部payload SHA，根0700、私有资料0600。env/完整Docker和Compose仅保留服务器，不输出密钥、用户日志或真实资料。
2. Backend `FROM` 实际固定f6dbe，仅覆盖模块、ports、schema、Redis及内存截图repository、截图service六个已批准文件；不安装依赖、不迁移、不重建无关源码。验证其余224运行输入保持、原202API逐项保留，仅新增批答路径及兼容schema字段，Settings有效值和启动单进程拓扑不变。
3. Web `FROM` 实际固定2124，仅增加新的LivePage/adapter相关增量模块及局部样式，精确修改必要入口引用。冻结旧315静态逐项保留或记录唯一必要的入口字节变化；不以当前Vite整包替换生产、不混入简历研发或国际服内容。核对旧功能模块图与所有公开功能入口。
4. 实际候选镜像先禁网、只读运行合成探针；覆盖capture-only无模型/无收费、多图图序、一任务一次计费、重复/越权/过期/取消及旧单图兼容。可用一次有界的实际视觉提供方合成两页验证：最多一个外部HTTP请求、无重试、短超时、有限输出，输入仅生成的无个人信息图片；不进入业务lifespan、真实DB/OSS/资料/会话/钱包，不保存原始响应。不能将该探针称为真实桌面设备已验收。
5. 只使用固定image和原完整Config/HostConfig/Mounts/网络，原始环境和Compose全量冻结并检查。先Backend后Web，重复受保护门禁及临近切换的Backend TCP/PID/netns核对；任何活跃普通/笔试/模拟面试、音频/截图工作、简历任务、资料处理或财务工作均延期，不清理活动或放宽保护。门禁读失败停止。
6. 回滚同样只恢复本轮已归属组件固定原image，执行重复门禁和身份确认；不得杀用户工作或回滚资料、账本、已有任务。
7. 部署后独立verify：完整输入/静态/接口/配置/非目标/NGINX；健康、登录、普通/模拟/笔试/简历入口；匿名私有接口401及no-store；多屏policy标记；短时聚合ERROR/traceback/HTTP5xx观察。只报告聚合结果。用户在完成后进行自己的真实桌面试用。

## 停止条件

受保护工作busy仅延期，不强行切换。镜像/源码/配置/payload/归属漂移、候选失败、未知错误或恢复失败均停止自动动作并报告。首次发布后的短时观察不等价于长期成功率、模型语义质量、Windows/macOS真实设备或P95验收。

## 首轮恢复后的第二轮执行约束

首轮因验收工具把四个内部HTML文件名直接当作公开URL，报 `public_route_unavailable`，已由原控制器完成受保护恢复；首轮发布目录和证据保留。第二轮重新绑定恢复后的实际Backend容器 `4d3653af6000dd031e6f090e1dbc2e50b22839d2cc0b2c39f6301335949210b2`、Web容器 `11f545c3b82e42b27c4467b71f3d1982006b6ab97280bae5527047927b8b0c97`，镜像仍为原f6dbe/2124，不能沿用首轮原容器身份。

第二轮独立服务器目录为 `/opt/offersteady/releases/20261019-cn-written-multi-screen-2`；38文件payload仅更新控制器验收映射、恢复后基线/授权与只读公开诊断摘要，业务六源码、17网页增量及禁网离线探针均与首轮字节一致。

- 控制器SHA-256：`e4f4c50f427e9c43ff91c0cf83beb22680e0fc8c6c1ebc8a4124287bfa6458ab`
- 输入SHA-256：`a1e0d1efe2eaef006eb6f15b16181ba20fd4fd1c09af9013767dd6f2f27d5b99`
- 授权摘要SHA-256：`a7fd15c5d157ac65f00606cf2daf7dc721b27ec0f55fdfd9a9b0e120704fbcbb`
- 恢复后基线SHA-256：`078084d37b8e909ec608f23f9dd7bb4e4bcfa18af3efaf22927b4dd2b001704f`

公开验收将 `index.html/guide.html/privacy.html/terms.html` 分别映射为 `/login`、`/guide`、`/privacy`、`/terms`，保留完整200和SHA要求；13个新增hash资源按原公开路径验证。不得放宽NGINX或把内部路径404当成通过。失败仅记录公开路径、阶段和安全状态，禁止写出响应体或用户资料。

26项映射回归及136项完整控制器保护回归均通过（完整回归包含映射用例）。七组用户工作门禁、TCP/PID/netns、归属检查、源/配置/静态/非目标检查和保护恢复条件保持。一次有界提供方QA只在实际候选业务输入及有效Settings完全等值时复用，不再次调用模型。

第二轮证据目录为主仓库 `artifacts/cn-written-multi-screen-20261019-release-r2/`。冻结、实际切换、独立verify及观察状态以[发布记录](../../../docs/releases/cn-written-multi-screen-20261019.1.md)真实收据为准，原始准备和首轮恢复历史保留。

## 第二轮实际切换回执

第二轮 `actual-deploy.json` 已取得 `deployed=true` 的实际回执，时间戳 `1792362979156`，即北京时间2026年10月19日06:36:19.156。Backend实际容器为 `d12beb7086a7ab6b51b31ea55236b4891a8663607a174c996659c7a8c253ddd3`，镜像 `sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88`；Web实际容器为 `75986fa2193dca8ef72a35efbd5b7d74dde71767a97a3e1a0b09076857ce5310`，镜像 `sha256:011d1f5de69f1208bf8b9c5b9496d4acddcbe090e6c159a0173214eb8efbbee2`。

26项公开验收全部通过；回执确认非目标容器和既有配置保持、简历优化保持开启、没有迁移或依赖变更。任务5.4按实际受保护切换完成勾选；任务5.5最终结果见末节，不以部署回执替代独立验收。

回执中的 `signature` 是创建时冻结快照，不能把其中的Backend `health=starting` 解释为后续实时健康状态。当前健康需以后续独立实时检查和观察收据确认；真实桌面试用仍由用户执行。

## 最终独立验收完成

第二轮发布成功，`actual-verify.json` 确认完整230运行输入、203接口路径、340有效配置字段、328网页静态文件及6个非目标容器保持预期，26项公开检查再次全部通过。`public-capture-policy.json` 确认公开策略接口200、`supportsCaptureOnly=true`、`maxImagesPerTask=4`，未创建业务工作或调用模型。

`short-observation.json` 记录北京时间2026年10月19日06:36:41.877至06:39:41.877的180秒聚合窗口：Backend healthy、两个组件running、restartCount均0，Backend340行/Web160行日志均未达4000行上限，ERROR、traceback、HTTP5xx均0。原始用户日志没有导出。这是短时发布验收，不代表长期P95或真实Windows/macOS桌面已经验证。

任务5.4和5.5均已完成。可在国服实际笔试页开启“多屏回答”，用网页按钮连续截屏（最多4张）后点击“回答”；本地5180仍是合成演示，桌面全局快捷键继续旧单图。一次有界模型QA通过候选镜像完全相同和Settings完全相同证明复用，第二轮没有再次调用模型。Git、国际服及助手分发均未操作。
