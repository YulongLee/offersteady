# 国服简历优化失败诊断热修复生产发布 — 20261018.1

状态：已上线并验收。北京时间2026-10-18 05:07:33.546仅切换CN Backend，05:08:35.669独立verify通过。用户已明确授权优化完成后部署，并许可一次纯合成真实Provider验证。实际服务器目录`/opt/offersteady/releases/20261018-cn-resume-optimizer-hotfix-2`。范围见[生产追加规范](../../openspec/changes/add-cn-resume-optimizer/hotfix-production-release.md)，本地修复历史见[20261018.3](cn-resume-optimizer-local-20261018.3.md)。

## 上线内容

仅修改本功能Provider、Service、Repository并新增diagnostics模块：34种固定无正文失败原因、owner安全中文说明、失败诊断与原路释放/退款同事务，以及合法JSON对象的单一BOM/外空白/整体完整小写json围栏兼容。保留结构、引用、语言、数字/联系方式、中英文事实/责任、重叠及草稿守卫；拒绝重复字段、非法/截断/非stop和非有限数字，不修补JSON或盲重试。旧失败记录没有分项诊断，仍按旧通用消息读取。

会员每天免费3次、其他100积分及仅付费前确认保持。没有DDL/迁移、环境/依赖/模型参数或预算、收费、Prompt、Web/NGINX/static、Global、助手、Admin或资料worker变更，没有Git提交/推送。普通/模拟/笔试、钱包/支付、资料上传和已发布性能优化保持。

## 实际组件和绑定

| 项目 | 最终值 |
| --- | --- |
| 固定实际父镜像 | `sha256:995ae331be9879d53309578f05056e081029e1018cc62ed89f45b81df5fcea2f` |
| 固定新Backend镜像 | `sha256:6f2a53f55ac6343c983234fedde62bd46432a1087c75705425c267971bf3d581` |
| 新Backend容器 | `b955c33e09508174c17df5113cad469eb63122f4726e2a25adbe8f010f7bd730` |
| 控制器SHA-256 | `e5ad4d319a85e0951b4a93b5c94978e08b8ac2abedf3061232e503bf0eafe9da` |
| 输入清单SHA-256 | `e6c6bc42b6d1e43cd1a0ebc2f1d1e7da2063c122420752cca2bd41cc0848eb3e` |
| 实际v3基线SHA-256 | `00e571478feea69cfb0c14099db86f79c653faf17c4aae0b9186457872f86943` |

已发布228输入中225项不变，3项既有文件调整、1项新增，候选229项；202条完整路径/schema与340个Settings及有效配置保持。候选直接派生实际父镜像，原image Config和全部父层不变。七个非目标容器身份、完整配置/挂载/网络摘要保持；原Web容器029e84e0…/20d6a03a…及305项静态/NGINX保持。Backend IP未变化，无需Web/Admin代理reload，未执行任何非目标重建。

## 验证结果

- 本地六文件283项通过，无失败/错误/跳过；四份源码SHA与实际候选相同。16条JSON兼容eval与原16条事实eval包装复测保持，原Prompt不改。
- 最终控制器60项合成回归通过；此前独立122项保护检查、v2独立10项挂载字段/计数边界及完整payload审查通过。
- dir2实际禁网、只读、无生命周期候选探针通过：229输入/202完整路径、0新增路径、原schema，真实合成DOCX/PDF通过；网络、数据库、写文件、线程、子进程、依赖解析、生命周期七副作用全部0。
- 再次禁网探针及完整七门禁后，直接Provider仅发送1次固定纯合成简历，19335毫秒成功，4维评分/5建议/6待补事实/806字符稿；解析和事实守卫全部通过。已消费的一次marker和成功receipt绑定候选、四源码、脚本、输出合同、合成用例与输入；没有额外请求或Prompt/事实规则修正，没有创建生产job/usage/账本/面试或访问钱包、真实资料。
- preflight及切换前重复全部七门禁；最后各exitCode0、保护计数0，容量样本年龄23.508秒。七项旧失败资料仅为信息计数，未清理，没有终止用户活动或放宽保护。
- 实际部署与独立verify同一b955…/6f2a…，Backend运行/healthy/重启0；7个公开GET200，HTML/build SHA逐项等于原静态；2个匿名优化能力/导出接口401及private,no-store。完整源、路径/schema、环境与非目标由冻结控制器重新核对。
- 最终短时脱敏观察实际覆盖Backend107.969秒、Web87.266秒，各ERROR/traceback/HTTP5xx均0，固定失败诊断聚合为空、未知消息0，未截断；未导出原始用户日志。不能称完整180秒观测或长期P95验证。

最终独立核对：final-release-audit.json（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/final-release-audit.json`），可复算脚本final-release-audit.py（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/final-release-audit.py`）。实际证据包括部署（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/production-deploy-v2.json`）、独立verify（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/production-verify-v2.json`）、一次合成Provider（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/production-provider-check-v2.json`）、安全最终证据（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/production-final-safe-evidence-v2.json`）、短时统计（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/production-short-observation-v2.json`）。

## 发布工具曾停止的情况

第一次dir1已实际prepare成功，候选同6f2a53f5…，随后preflight以non_target_identity_or_configuration_changed停止，尚未真实Provider请求或生产切换。只读差异仅PG Mounts摘要不同，Config/HostConfig/网络和容器启动身份保持；不能据摘要宣称PG实际改挂载。

服务器随后只读确认七个非目标完整Mounts条目多重集保持；PG两条的原序d6d61…与稳定排序229772…精确复现该摘要差异，确认是inspect最外层排列误报。root批准canonicalMounts仅按每个完整canonical JSON排序，全部字段/值/重复数量和嵌套数组顺序保持，Source/Destination/RW/未知字段及HostConfig仍受保护。新增15项回归证明真实字段/条目/重复变化仍拒绝。新dir2/controller-v2/v3基线重新冻结、审查和实际prepare/preflight通过，没有原地改旧prepared包或放宽门禁。

旧dir1控制器8a01d939…、input28c3b4a5…、候选/停止/安全差异及完整顺序证明保留：preflight停止（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/production-preflight.json`）、顺序证明（本地历史记录：`../../artifacts/cn-resume-optimizer-hotfix-20261018-release/mount-order-proof.json`）。本次热修复未触发生产回退；原功能此前发布的其他失败和恢复记录仍见[原生产记录](cn-resume-optimizer-20261018.1.md)。

## 验收限制

一次合成真实Provider成功只证明当次链路和校验通过，不足以还原原用户旧invalid_output的精确触发项、证明其原任务成功或覆盖所有简历和模型采样。旧任务未代为重跑，没有真实用户端到端/钱包操作验收；用户可在[国服简历优化](https://mianshiwen.cn/app/resume-optimizer)使用原已上传简历测试。活动门禁为瞬时保护，短时健康/错误统计不作绝对零影响或长期模型质量/性能保证。

## 后续用户反馈：仍有严格校验失败（研究中）

上述实际部署、一次合成模型与短时验收是真实完成记录，不代表所有后续真实简历都会通过。用户上线后新任务读取3437字符/noJD，28030ms后以facts/fact_english_content_added失败，-100/+100各1且released；不知道具体新增词，未保存原模型输出，也未读取用户正文作夹具。另确认现有Web编译页面忽略后台errorMessage，因此用户看不到固定原因。后续[11.x研究草案](../../openspec/changes/add-cn-resume-optimizer/english-token-and-error-display-research.md)拟对齐CN Prompt及真实可见的安全白名单说明；当前无实施GO、未开发或再次部署，旧任务不代为重跑。
