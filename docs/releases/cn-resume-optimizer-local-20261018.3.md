# 国服简历优化失败定位本地修复 — 20261018.3

状态：本地源码、自测和独立审查完成，未发布；线上仍为已发布的20261018.2。用户原失败任务未重跑，未调用真实模型，未操作Git、Global、助手或Admin。范围见[失败诊断追加规范](../../openspec/changes/add-cn-resume-optimizer/failure-diagnostics.md)与[逐场景验收](../../openspec/changes/add-cn-resume-optimizer/verification.md)。

## 已知问题与限制

只读生产元数据表明，近期一项任务已读取3437字原文，在33048毫秒后以`invalid_output`失败；积分账本各一笔-100与+100，净额0。MinerU解析/读取不是该次失败阶段。旧版未保存具体解析或校验原因，不能事后断言是JSON格式、依据引用还是事实检查，更不能说用户上传不正确。证据：`artifacts/cn-resume-optimizer-failure-20261018/{failure-aggregates.json,refund-and-http-summary.json}`。

本地修复新增34种固定阶段/原因，不保存模型原始输出、简历、JD、字段值或身份信息到诊断或日志。诊断存于既有payload，与失败及原路释放同事务，原owner/claim/revision/source/取消删除屏障保持。页面继续用原errorMessage字段显示固定中文说明，内部诊断不出公共wire；只有确已released的新失败才附退款说明。旧记录仍只能显示通用错误。

模型结果现在可严格兼容开头单一BOM/外层空白及整体单一完整小写json代码围栏。依然拒绝说明文字、多对象、多围栏、重复字段、非法/截断内容、非stop结束、非有限数字；不修补JSON，不自动重试。结构、原文引用、语言、数字、联系方式、英文/中文事实与责任、重叠及最终草稿检查保持。

## 实际验证

在CN独立工作区执行六文件后端全套，283通过，0失败/错误/跳过，JUnit用时53.485秒；包括原147项、新增Provider113项、服务及计费23项。使用本地真实隔离PostgreSQL、合成资料和MockTransport；Python非回环网络连接/解析被阻断。没有真实模型请求或线上扣费。既有FastAPI TestClient有一项依赖弃用警告，本轮不改依赖。

精确命令：`PYTHONPATH=apps/backend:apps/backend/tests /Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python /Users/liyulong/liyulong/1_projects/offersteady/artifacts/cn-resume-optimizer-failure-20261018/local-hotfix/run-combined-tests.py`，工作目录为`/Users/liyulong/.codex/worktrees/cn-resume-optimizer/offersteady`。结果及输入SHA：`artifacts/cn-resume-optimizer-failure-20261018/local-hotfix/{combined-junit.xml,combined-output.txt,verification.json}`。

16条新增JSON兼容AI评测通过，原16条事实评测逐条经新包装复测保持；原Prompt及原评测不变。真实PG验证免费/积分释放一次、事务故障回滚、旧任务、未知/伪造诊断、取消/任务删/源删迟到回调、租约过期的日志与落库归因。独立审查无P1/P2，另执行8个无DB/网络运行时组合。证据：`artifacts/cn-resume-optimizer-20261018-failure-diagnostics/independent-audit/`。

以已发布228项源码映射核对：225项字节不变，只改本功能Provider/Service/Repository三文件，新增diagnostics一文件；完整映射229项。事实守卫逐AST对比只增加固定异常原因。schema、Prompt、MinerU、导出、原钱包、模拟面试、既有鉴权/状态优化均无改动，无DDL。会员每日3次/其他100积分保持。9份新合成HTTP响应的完整键/类型结构与冻结合同一致，旧JSON及Web夹具SHA仍为79abf3849d4f4cfaa43ffb5c0f1007f1fc4d17972f36fbb5bc73cdd3609ce857。

## 交付边界

本次没有改前端、API结构、Prompt或导出，所以未重复已有Web480项、页面截图和9页导出渲染。上述为本地合成兼容与回归证据，不能证明真实模型质量或已修复原任务的具体根因，也不能称线上已更新。后续生产发布须从当时实际Backend镜像冻结此四文件增量并执行活动门禁、候选验证、验收及固定回退；不能覆盖原线上组件或结束真实用户活动制造空闲。
