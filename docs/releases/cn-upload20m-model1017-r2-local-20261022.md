# 国服20MiB与1017联合发布：门禁第二版本地验证

用户已授权测试后部署国服。发布前第一版门禁发现22条历史回答预留和一份仍有效准备页lease，尚未切换生产组件。本记录只说明第二版门禁的开发依据，不把准备完成当成已上线。

## 校正依据

只读聚合确认22条 `answer` 类型reserved预留均超过7天及应用实际TTL，创建时间均早于原Backend进程，相关用户没有live会话。`BillingService.reserve_usage` 会先按当前用户惰性释放过期预留，再读取既有usage；回答只由Backend同步/进程内线程执行，资料worker不恢复answer。因此这些记录是旧进程遗留库存，不能与执行中的账务等同。

第二版只把类型精确为answer、创建时间为正且严格早于应用TTL截止点和冻结原Backend出生时间的预留计为信息。0、负、NULL、未来或边界相等时间继续保护；其它usage、未知状态、索引预留、订单/回调全部继续保护。仅调整只读分类，不改变记录、积分、会员、收费或余额。

原Backend时间锚点由新鲜Docker StartedAt派生，整数毫秒为1792362938555。input/manifest及冻结原容器Id/StartedAt必须一致；发布后继续使用该原锚点，不使用新容器的出生时间。

## 文件与验证

- 新控制器：`scripts/release_cn_upload20m_model1017_v2.py`
- 新支持包：`scripts/release_support/cn_upload20m_model1017_20261021_r2/`
- 独立生产准备目录：`/opt/offersteady/releases/20261021-cn-upload20m-model1017-2`
- 原第一版控制器、支持包和准备目录保持完整。
- 第二版正式保护回归78项通过，包含真实执行的合成SQL边界矩阵、固定原进程锚点、无账务写入及原失败恢复场景。模型与上传测试另有记录，不重复相加为本轮测试。

所有普通/模拟/准备页面lease、音频/连接、未完成文字/截图、资料、简历优化及TCP保护继续执行，准备页有用户时仍不能切换。门禁没有新增准入围栏，重复检查只缩小竞态窗口，不能据此承诺完全不存在发布瞬时重试。

关联规范：[模型发布Spec](../../openspec/changes/unify-models-v41-flash-1017/specs/verified-model-1017-routing/spec.md)。
