## Context

OfferSteady 已有 `/r/{slug}` 安全跳转、有效访问、注册身份绑定、订单归因与推广后台，也有独立的邀请积分关系。现有支付表能权威确认 `paid`，尚未形成统一的退款事实表。因此合作伙伴计划应复用推广事实，以追加式佣金账本承接支付和后续退款调整，并避免把任何工作放进面试、ASR、AI 回答或支付回调事务。

首版面向国内站，运营方每月人工打款。普通合作伙伴只能看到聚合结果，运营后台完成审核和支付登记。

## Goals / Non-Goals

**Goals:**

- 完成“主动加入 → 专属链接 → 注册归因 → 付费计佣 → 观察期 → 月度申请 → 后台结算”的可用闭环。
- 复用推广中心已有采集和归因，不复制 visitor、注册或订单事实。
- 用不可变、幂等、整数金额账本支持重跑、退款冲正和财务审计。
- 与邀请积分互斥，并将读取/投影/结算隔离在非实时控制面。
- 通过默认关闭的配置开关安全发布。

**Non-Goals:**

- 自动银行、微信或支付宝打款；自动开票或代扣税计算。
- 多级代理、下线团队、排行榜、公开被邀请人名单。
- 跨设备概率归因、旧订单猜测回填、实时强一致报表。
- 改动登录、面试、桌面 Companion、ASR、RAG、AI、截图或支付确认链路。

## Decisions

### 1. 合作伙伴链接是推广链接的受限类型

`promotion_links` 增加 `link_kind=operator|partner` 和可空 `owner_user_id`。合作伙伴加入事务确保一个用户只有一个档案和一个 active partner link，链接绑定系统渠道“合作伙伴”，目标固定为 `/`。

这样 `/r/{slug}`、Cookie、有效访问和注册 claim 完全复用现有逻辑。替代方案是再建 `/partner/{code}` 链路，但会复制安全跳转与归因代码，且两套口径容易漂移，因此不采用。

### 2. 用 reward program claim 保证积分与现金互斥

新增 `growth_acquisition_reward_claims`，以 `acquired_user_id` 为唯一键，值为 `points_referral` 或 `cash_partner`。邀请积分激活事务和合作伙伴归因投影都先锁定该用户的 claim：已有同类 claim 幂等，已有异类 claim 则不再发放另一类价值。

现金 claim 在第一次可证明的 partner 注册归因被投影时建立；如果积分激活已经完成，partner 访问仍可进入推广聚合，但其订单不计佣。替代方案是在每笔订单临时检查邀请表，无法表达稳定归属且容易产生竞态，因此不采用。

### 3. 佣金使用订单级追加账本

`partner_commission_ledger` 保存 `earning`、`refund_reversal`、`payout_reserve`、`payout_release`、`payout_paid` 五类条目；每条都有 `source_type + source_id + rule_version` 幂等键、整数分金额、费率和时间快照。余额通过求和得到，不原地修改历史金额。

首版支付投影读取 `billing_checkout_orders.status='paid'`、注册时间和锁定 partner link，按 2000 bps 写 earning；7 天后计入 available。当前支付域没有统一退款表，退款/拒付先由受权管理员以权威渠道退款单号录入 adjustment，后续支付渠道接入退款回调时仍写同一种幂等 reversal，不需要迁移账本。

替代方案是在 partner profile 上维护累计金额，虽然查询简单，但无法可靠冲正、重跑或审计，故不采用。

### 4. 投影是有界的显式后台任务

增加 `project_paid_orders(limit)`，由 promotion analytics worker 的周期运行调用，也可由管理员触发有界同步。任务只读取已支付订单并以数据库唯一约束幂等写入，不修改支付订单，不从支付回调同步调用。报表允许分钟级延迟并展示更新时间。

替代方案是在支付成功事务内同步计佣，会扩大支付失败面和锁竞争，不符合现有热路径隔离原则。

### 5. 月度结算采用状态机和原子预留

申请条件为可用佣金至少 10000 分、每个 `Asia/Shanghai` 月最多一笔。创建 request 与负向 `payout_reserve` 在同一事务完成。状态只允许：

```text
requested -> approved -> paid
          -> rejected（同时 payout_release）
approved  -> rejected（同时 payout_release，限未支付）
```

`paid` 写 `payout_paid` 以把 reserved 余额转入 settled 统计。所有管理动作进入现有 admin audit，并要求新增 `promotion.payout.manage` 权限。

若打款完成后才发生退款或拒付，追加 reversal 会形成负数可用余额并由后续佣金抵扣；用户与后台均保留真实负数，不把债务静默显示为零。

首版不在产品内保存银行卡、身份证或收款码；运营人员通过既有客服联系用户，后台只记录不敏感的支付参考号。这样降低敏感数据范围。替代方案是内置收款账户管理，需额外加密、访问控制和合规流程，本期不做。

### 6. API 与页面边界

用户 API：

- `GET /api/v1/partner-program/me`：未加入说明或已加入聚合看板。
- `POST /api/v1/partner-program/join`：接受 agreement version 并幂等加入。
- `POST /api/v1/partner-program/payout-requests`：按规则申请当月全部可用余额。

管理 API 位于 `/api/v1/admin/promotion/partners`，提供合作伙伴列表、结算列表、投影、退款调整和状态流转。用户响应不返回被推广用户级明细。

Web 在首页 Footer 增加入口并新增受登录保护的 `/app/partner-program` 页面；Admin 在推广中心新增“合作伙伴”标签，不改变现有五个标签和指标。

### 7. 配置与安全默认值

新增 `OFFERSTEADY_PARTNER_PROGRAM_ENABLED=false`、费率 2000 bps、订单窗口 90 天、退款观察期 7 天、最低结算 10000 分和协议版本。生产开启时要求 promotion 已启用且数据库可用。接口使用现有用户 JWT 和管理 RBAC；slug 不泄露用户信息，所有金额转换使用整数。

## Risks / Trade-offs

- [当前没有统一退款事实] → 首版只接受管理员依据支付渠道退款单号录入的幂等冲正；自动退款接入前后台明确标记“退款同步方式：人工”。
- [归因或投影延迟导致看板非实时] → 展示最后更新时间，重跑幂等；不以牺牲支付/面试稳定性换取秒级更新。
- [现有积分邀请与 partner claim 竞态] → 两种认领在同一唯一键上加事务锁和唯一约束，数据库决定唯一结果。
- [用户把预计佣金理解为可提现] → 页面明确区分待确认、可提现、审核中和已结算，并展示观察期。
- [人工结算发生误操作] → 有限状态机、必填原因、权限、审计和不可变账本共同约束。

## Migration Plan

1. 部署新增表、索引、系统渠道和可空 link 类型字段，保持 partner 功能开关关闭。
2. 发布后端 API、投影任务和管理页；运行迁移与自动化测试。
3. 发布用户页面和 Footer 入口，但开关关闭时展示“活动筹备中”且不创建数据。
4. 运营确认协议、税务与人工结算 SOP 后开启开关，小范围验证一笔合成或内部订单。
5. 监控投影延迟、账本不平衡和 payout 状态；异常时关闭 partner 开关即可停止新增加入/计佣，现有面试和支付不受影响。

回滚时先关闭功能开关，再回滚应用版本；新增表保留用于审计，不执行破坏性删表。

## Open Questions

- 自动退款回调接入前，运营人员使用哪一份渠道退款流水作为录入凭证，需在正式开启前写入结算 SOP。
- 现金结算涉及的代扣代缴和凭证要求需由运营主体的财税顾问确认；本实现只记录税前佣金与支付参考号。
