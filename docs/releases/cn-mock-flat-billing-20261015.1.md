# 国服模拟面试简化收费：2026-10-15 上线

用户在 [本地验证](cn-mock-flat-billing-local-20261015.1.md) 完成后明确授权国服上线。2026-10-15 **05:29（北京时间）** 已同步切换国服 Backend/Web，发布目录 `/opt/offersteady/releases/20261015-cn-mock-flat-billing-1`。关联 [需求](../../openspec/changes/simplify-cn-mock-interview-billing/proposal.md)、[能力场景](../../openspec/changes/simplify-cn-mock-interview-billing/specs/cn-mock-flat-rate-and-deadline/spec.md) 与 [发布保护脚本](../../scripts/release_cn_mock_flat_billing.py)。

## 生效规则

所有有效时间会员每天免费 1 场，北京时间 00:00 更新次数；无免费次数时创建一场一次性扣 100 积分，不收分钟费。积分包本身不授予会员免费权益。

首次成功开始后 60 分钟自动结束，准备阶段不计时；暂停、出题等待、断线、刷新和服务重启均不延长期限。到时停止收音和朗读，保留已确认提交的回答并生成报告；证据不足时不编造分数。

历史账本保留，旧进行中场次停止新增分钟费。沿用原有可信故障退款规则并按实际已扣金额补偿一次；主动取消和删除记录不退创建费、不恢复次数。普通面试、笔试、会员套餐价格、两条保存上限与 Global 原权益保持。

## 实际基线与发布镜像

| 项目 | 标识 |
| --- | --- |
| 原 Backend 运行镜像 | `sha256:ec510532ca598878e147c4277e6da9776924fbf056ed942ab4cc2bf110f398bb` |
| 新 Backend 镜像 | `sha256:eb242b56fded1473659c2f4517f07b42eeaff138b59029e5819fbaa972b12488` |
| 新 Backend 容器 | `781edda9fa92f74742450a35625f4a3a8744f9f53d9ade3832cc170440673b7b` |
| 原 Web 镜像 | `sha256:df74779852799933e49aee117d1c45aaf3b789d29c8413caa994219ae50ab6a3` |
| 新 Web 镜像 | `sha256:695959e95ef1ca20367c62333acd42e6aaf05df5c16692da039d8ca873cc0f2c` |
| 新 Web 容器 | `f65d1d39a79e11de4545175017040ffa2d1746c8ab1e18ac06f7915de481a549` |
| Backend 回滚镜像（含 1.3.5 清单） | `sha256:c24d1237ca4790eba53f07b46ff1ba35a9778dea36b9e5b070dcee4c7e85766c` |
| Web 回滚镜像 | 上述原 Web 镜像 |

新标签为 `offersteady-cn-backend:mock-flat-billing-20261015-1` 和 `offersteady-cn-web:mock-flat-billing-20261015-1`，运行标签 `compose-backend` / `compose-web` 同步指向新镜像。现有 `current` / `backend-current` / `web-current` 源目录指针未作为本次源码基线；未来发布仍需读取实际容器 Image。

后端从实际镜像增量修改 5 个 Python 文件：模拟面试 Repository、Runtime、Jobs、Audio，以及普通实时通道的模拟面试隔离防护。实际基线测试发现旧普通通道可对模拟面试重新触发分钟费，因此只补入 RealtimeSpeechService 的 4 个准入防护；其余 165 个方法保留，包括已发布的轻量 heartbeat 和性能回执。到期异步关闭需要的有界资源清理已携带，普通提交仍保持原有等待关闭方式；此前本地下一题等待优化及生成诊断没有随本次发布。

Web 仅编译本轮模拟面试页面及报价刷新辅助方法，复用实际运行的 React、认证、请求、播放和 Word 导出模块；8 个其他模块只重链接依赖 URL。保留 188 个旧静态资产及 92 个其他公开文件，4 个 HTML 仅替换入口 URL。新入口 `main-70489fb1.js`，新模拟模块 `MockInterviewPage-86ff5137.js`；8 字符名称保持现有 immutable 缓存策略。`offersteady-build.json` 标识 `cn-mock-flat-billing-20261015.1`。

下载清单 SHA-256 仍为 `76ba8b6009071d4c4c0b824b6bbbf1c05c7d848f95c1ab08649c9e9e05c4a76a`，Windows/macOS 三个平台仍是 1.3.5。本轮显式将容器可写层的当前清单携带到候选与回滚镜像，防止旧基础镜像内的 1.3.2 清单恢复。临时空锁文件不作为业务源码携带。

## 验证与切换

- 本地开发：Backend 353 项、本轮 Web 43 项通过；类型检查和编译通过。原全量 Web 的 3 项 Nginx 基线失败见本地记录；本次实际发布保留线上 Nginx，其 SHA `b7d060995b6c01bbeeb46a851d5357d3292a173cb31f117cac9d039e67e96894` 未变。
- 按实际国服候选包重测：275 passed；仅明示排除本地诊断日志与 Global 专属 TTS 两个不适用案例。另确认 4 个关闭工作线程及排队观察任务取消后，实际采集资源只释放一次。
- 切换保护及补充只读门禁：71 项合成测试通过。准备前及切换前反复检查普通/笔试/模拟 live、活跃准备、页面租约、音轨、未完成回答和资料任务；受保护计数均为零，模拟历史仅 27 条 completed。
- 隔离 Chrome 以真实生产 CSP 运行 8 个场景：1440/390 像素 × 首页、会员免费、积分收费、到期报告。无脚本/CSP 错误、无横向溢出、未加载旧入口；两个报告场景实际下载并校验 Word。全部 API 使用合成响应，没有写业务数据。
- 服务器候选镜像隔离验证：固定费用策略、147 个静态后端文件、294 个网页文件及 Nginx 语法通过；不连接生产数据库或模型供应商。
- 只重建国服 Backend/Web。环境、模型、挂载及服务配置未改；另外 6 个服务的 ID、镜像和启动时间保持。后端 healthy，两目标 RestartCount 均为零。
- 公网 30 项检查通过：健康、登录、模拟页面、公开 capabilities、匿名列表认证保护、下载清单以及全部活动 JS 依赖和旧入口资产。公开文件 SHA/MIME/缓存一致，当前页面使用新入口，三平台 1.3.5 清单保留。
- 本变更 OpenSpec strict 校验通过；6 份本轮文档的 12 个本地链接目标存在，`git diff --check` 通过。

首次未发布的 Web 桥接候选在真实浏览器探针中发现 request/socket 导出映射错误，修正并重新冻结后才切换。错误候选的准备记录单独保留为 `prepared-browser-map-failed.json`，没有接入运行服务。

没有生产表迁移、账本改写、测试账号创建或真实模型/收费调用。物理麦克风和真人完整面试留给用户验收；现有正式 1.3.5 助手可继续使用。测试前刷新网页，再进入 [模拟面试](https://mianshiwen.cn/app/mock-interviews)。

## 回滚

发布目录保留私有原环境与容器配置、`prepared.json`、`candidate-verification.json`、`deployed.json` 和实际候选输入；私有环境文件没有下载或提交 Git。切换脚本在验证失败时自动以不可变镜像 ID 回退两目标并检查环境、配置、挂载及健康。

后续人工回滚需重新核查活跃用户工作并使用以下已保存镜像，恢复两组件的运行标签后只重建对应服务；不得使用旧目录重建或删除数据库/账本。Backend 必须用含 1.3.5 清单的回滚镜像。回滚会恢复原收费规则，需要同步 Backend/Web 后再开放测试。

| 服务 | 回滚标签 |
| --- | --- |
| Backend | `offersteady-cn-backend:mock-flat-billing-rollback-20261015-1` |
| Web | `offersteady-cn-web:mock-flat-billing-rollback-20261015-1` |
