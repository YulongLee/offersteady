# 国服简历优化生产发布 20261018.1

状态：已于 2026-10-18T04:14:12+08:00 完成国服 Backend → Web 切换；独立验收与短时观察通过。用户授权：“这个功能上线到国服吧。我这边测试下效果”。服务器最终目录：`/opt/offersteady/releases/20261018-cn-resume-optimizer-3`。

## 上线行为

沿用 [本地验收 20261018.2](cn-resume-optimizer-local-20261018.2.md)：时间会员按北京时间每天免费 3 次；非会员及超额每次 100 积分，仅在付费操作前确认。页面保持简洁，提供评分、修改建议、事实依据、可编辑草稿、真实 DOCX/PDF 下载、独立另存及历史管理。

模拟面试、普通面试、笔试、资料上传、原计费和已发布性能优化保留。模拟面试仍每天会员免费 1 场、其他 100 积分/场、60 分钟上限。本次不更新 Global、助手、Admin、资料 worker，不提交或推送 Git。

## 实际基线与最终镜像

| 组件 | 实际父镜像 | 最终固定候选镜像 |
| --- | --- | --- |
| Backend | `sha256:4c305868ca6799cb7b8a69afd691f2e2e966785dfce827a0e04c51fa431fd656` | `sha256:995ae331be9879d53309578f05056e081029e1018cc62ed89f45b81df5fcea2f` |
| Web | `sha256:695959e95ef1ca20367c62333acd42e6aaf05df5c16692da039d8ca873cc0f2c` | `sha256:20d6a03a6acdc923f02cc786af2cdd862599b4e65ef1d2dbc9fd77be7c163610` |

最终 Backend 容器 `4667f8b88636e195c7b51008e79c5941730eb15a16d42f7f0ff4c92dcfba3234`；Web 容器 `029e84e02966c215cec60db5974cc708a1887161b28d145fa7cf856384a66256`。控制器 SHA-256：`8a33ad05e311a4e2ac5098c73d85d34803be3a9033f709978d19b039a7bac09d`。

重新冻结各组件实际运行镜像、配置及完整输入。18 个 Backend 增量包含 6 个既有接入输入和 12 个新文件，完整候选 228 项；原 195 条路径/schema 与 2,337 个既有方法保持，新增 7 条路径/9 个操作。原 338 个有效配置字段保持，唯一环境增量为启用 CN 简历优化开关。

Web 基于实际镜像追加 11 个文件，294 → 305 项。289 个旧文件字节保持，4 个 HTML 仅替换入口模块 URL，另更新构建标记；旧 hash 资源、媒体、SEO、价格和错误页保留。NGINX 仅新增工作台 `/resume-optimizer` allowlist 字面量。最终入口 `main-edf518ca.js`。

## 验证与门禁

- 本地后端 147 项、网页 480 项、类型检查和构建通过；真实导出格式 11 项及 9 页渲染检查通过，相关导出源/字体未变。
- 实际拼装产物 Chrome 24 项宽窄屏操作通过，含原模拟列表/报告、普通面试、笔试、资料上传、钱包及新功能操作，错误/CSP 违规/模型调用均为 0。
- 最终控制器 86 项合成安全回归及独立审查通过，保护未知/失效样本、漂移、归属、分步发布与受保护回退。
- 实际 Backend 镜像完整探针通过：228 项输入、202 条路径、原配置、3 次/100 积分合同和真实合成 DOCX/PDF；网络、数据库、写文件、线程、子进程、依赖解析、生命周期副作用均为 0。
- 实际 Web 镜像以 nginx 用户检查 17 项公开文件/配置可读；同固定镜像启动隔离 NGINX，6 条页面/标记路径和 11 个新资源全部 200、正文 SHA 全部相符，隔离实例已清理。公开文件 0644、目录 0755，私有环境和冻结配置 0600。
- preflight、迁移前、每个组件切换前均重复七个只读门禁；最终门禁聚合通过。只执行/核对 `0054_cn_resume_optimizer.sql`，保留钱包 trigger、其他约束和历史行；再次执行时按 journal 跳过已应用迁移。非目标六个容器身份保持。

证据：部署结果（本地历史记录：`../../artifacts/cn-resume-optimizer-20261018-release/production-deploy-v3.json`）、实际候选独立审查（本地历史记录：`../../artifacts/cn-resume-optimizer-20261018-release/independent-actual-candidate-audit-v3.json`）、真实隔离 NGINX（本地历史记录：`../../artifacts/cn-resume-optimizer-20261018-release/isolated-nginx-routes-v5.json`）、最终门禁（本地历史记录：`../../artifacts/cn-resume-optimizer-20261018-release/production-final-idle-gates-v3.json`）。

## 发布过程中的问题与修复

第一次 prepare 因实际 Web 为 build-only Compose、渲染配置无 `image` 字段而停止，尚未迁移或切换。修复后仅接受 Web、非空 build、精确 `compose-web` 引用且标签指向原固定镜像，不改写原配置。

第二次尝试执行 0054 并切换两组件，公开验收出现 HTTPError，原异常未保存具体路径/状态；完整门禁和归属检查后恢复原固定镜像，保留 additive 表。之后用同一固定候选隔离复现六条路径全部 403：root 上传脚本误把公开文件设为 0600，原版为 0644，导致 nginx worker 无权读取。这解释了公开验收失败，不能把隔离复现的状态当作原异常直接记录。

第三次使用重新冻结的实际容器身份、新发布目录和独立标签。安装器显式设置公开/私有权限，NGINX 构建用 copy2 保留权限；加入输入模式和实际 nginx 用户读取检查，并在切换前通过真实隔离 NGINX 的 17 项访问验证。私有配置始终留在服务器。完整历史见 尝试记录（本地历史记录：`../../artifacts/cn-resume-optimizer-20261018-release/attempts.json`）。活动门禁为零及完成恢复，不能证明所有页面访客在第二次尝试期间都未受影响。

## 独立验收和限制

独立 verify 已通过：当前两容器属于本次发布，完整源/静态/配置/健康相符；公开健康、登录、构建标记、新简历页面、模拟/普通/笔试入口均为 200，页面/标记正文 SHA 匹配；匿名能力和下载均为 401、private/no-store。Backend 有效观察 148 秒、Web 114 秒，当前新容器日志的 ERROR、traceback、HTTP 5xx 均为 0。观察不包含已移除的第二次失败容器历史日志，也不代表所有用户零影响。

证据：独立验收（本地历史记录：`../../artifacts/cn-resume-optimizer-20261018-release/production-verify-v3.json`）、短时脱敏统计（本地历史记录：`../../artifacts/cn-resume-optimizer-20261018-release/production-short-observation-v3.json`）。发布过程不使用真实用户资料作为夹具，不调用真实模型、不创建真实面试、不代用户扣积分。实际模型效果及长期 P95 由后续正常使用验证，短时健康检查不作长期性能保证。
