# 国际服多语言与支付能力恢复

## 原因

- 国际服 Web 已包含多语言入口，但线上 Backend 仍运行旧发布目录，只接受中文和英文。
- 旧 Backend 不识别 Creem 正式商品返回的 `mode=prod`，商品同步被判定失败，支付提供方因此保持停用。
- 此前发布版本号已更新，但 `current` 仍指向旧代码目录，导致前后端能力不一致。

## 恢复范围

- 将国际服 Backend、Global Web、Admin 和 Analytics 切换到同一完整基线。
- 恢复中文、英文、日语、韩语、法语、德语、西班牙语、葡萄牙语、俄语和意大利语的语言注册、ASR 路由及分语言提示词链路。
- 恢复 Global 支付目录、Creem 商品读取、商品映射校验和后台支付管理入口。
- 保留 PostgreSQL、Redis 和用户数据；未重建数据服务。

## 验证

- 多语言与 Global Commerce 后端定向回归：55 passed。
- Shared Protocol 回归：32 passed。
- Global 语言选择器回归：2 passed。
- Global Web 生产构建、Backend、Admin 和 Analytics 镜像构建通过。
- 线上十种 Production 语言均加载完整 system、quick 和 detail 提示词。
- Creem 正式环境读取 8 个商品；4 个在售套餐的版本、金额、币种、计费方式和状态全部匹配。
- `/api/v1/global-commerce/readiness` 返回 `ready=true` 且无 blocker。
- 公网 `/healthz` 与构建清单正常，发布后 Backend 日志无 5xx/Traceback，进行中面试为 0。

完整仓库回归仍有若干与本次恢复无关的既有快照、耗时阈值和首页内容断言未通过；本次上线以多语言、支付、协议、构建和线上冒烟结果为准，未把这些失败标记为已解决。

## 发布与回滚

- Host：`47.84.65.103`
- Release：`global-capability-restore-20260919.1`
- Release path：`/opt/offersteady-global/releases/20260919-global-capability-restore-1`
- Current：`/opt/offersteady-global/current`
- Rollback images：
  - `offersteady-global-backend:rollback-before-capability-restore-20260919`
  - `offersteady-global-web:rollback-before-capability-restore-20260919`
  - `offersteady-global-admin:rollback-before-capability-restore-20260919`
