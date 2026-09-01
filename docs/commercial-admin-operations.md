# 商业管理后台运维

管理后台与用户端独立构建，默认关闭。生产发布数据库和后端代码不会自动暴露管理入口。

## 必需配置

```env
OFFERSTEADY_ADMIN_ENABLED=false
OFFERSTEADY_ADMIN_ALLOWED_ORIGINS=["https://admin.mianshiwen.cn"]
OFFERSTEADY_ADMIN_SESSION_TTL_SECONDS=28800
OFFERSTEADY_ADMIN_RECENT_MFA_TTL_SECONDS=300
OFFERSTEADY_ADMIN_SESSION_SIGNING_SECRET=<至少 32 字节随机值>
OFFERSTEADY_ADMIN_ENCRYPTION_KEY=<至少 32 字节随机值>
OFFERSTEADY_ADMIN_MAX_PAGE_SIZE=100
OFFERSTEADY_ADMIN_QUERY_TIMEOUT_MS=3000
OFFERSTEADY_ADMIN_RATE_LIMIT_PER_MINUTE=120
OFFERSTEADY_ADMIN_MAX_CONCURRENT_QUERIES=4
```

两个管理密钥只能进入服务器 Secret，不能提交 Git、写入 `VITE_` 变量或发送到浏览器。

管理会话默认覆盖 8 小时工作日，但令牌仍只保存在当前浏览器标签页会话中；关闭标签页后需要重新登录。高风险操作的近期验证窗口仍为 5 分钟，不能因为管理会话尚未过期而跳过。登录页的“记住手机号”只在管理员主动选择后保存规范化手机号，不保存验证码、普通访问令牌或管理令牌。

## 登录连续性与短信故障判断

管理前端 Nginx 使用 Docker 内置 DNS 动态解析 `backend` 服务。只重建 Backend 容器时，Admin 会在短 DNS 有效期内自动连接新地址，不应要求重启用户端 Web。如果管理端发送验证码出现 502/503/504，而同一时刻用户端验证码正常，优先检查 Admin 代理和 Docker 服务发现，不要轮换阿里云短信密钥。

排查顺序：

1. 请求 Backend `/healthz`，确认后端进程已经可用。
2. 在 Admin 容器内解析 `backend` 并请求 `/api/v1/auth/sms/send-code`，确认代理已拿到新地址。
3. 检查 Admin Nginx 错误日志中是否仍访问旧容器 IP。
4. 只有 Backend 自身返回短信供应商错误时，才检查阿里云签名、模板、AccessKey 和限流。

手机号已记忆但管理会话过期时，登录页会预填手机号；这是正常安全边界，不代表短信服务不可用。短信发送成功后按钮会按服务端冷却时间倒计时，倒计时期间不要重复请求。

## 首位管理员

先让管理员手机号完成一次普通短信登录，确保 `auth_users` 已存在。随后在服务器后端容器中执行：

```bash
offersteady-admin-bootstrap --login-id 'sms:<该账号在数据库中的登录标识>' --role super_admin
```

命令输出 TOTP provisioning URI 和一次性明文 secret。使用身份验证器扫描并离线保存恢复信息；数据库只保存加密值。再次运行会轮换 TOTP 并提升授权版本，使旧管理会话失效。

## 灰度顺序

1. 保持 `OFFERSTEADY_ADMIN_ENABLED=false` 部署新后端。
2. 运行 `0014_commercial_admin_console.sql` 或首次通过受控命令初始化管理仓库。
3. 创建首位超级管理员并验证 TOTP。
4. 配置 `admin.mianshiwen.cn` DNS、HTTPS 和独立反向代理。
5. 使用 `docker compose --profile admin` 启动管理前端。
6. 设置管理来源并将总开关改为 `true`，只向首位管理员开放。
7. 检查审计完整性、错误率和查询延迟后再增加其他角色。

Backend 单独发布或重建后，应额外验证 Admin 验证码请求；无需重建 Web 或桌面助手。若生产环境显式配置了 `OFFERSTEADY_ADMIN_SESSION_TTL_SECONDS`，该配置优先于镜像默认值，发布时应确认仍为预期的 `28800` 秒。

## 回滚

将 `OFFERSTEADY_ADMIN_ENABLED=false` 并停止 `admin` profile。不要删除管理表和审计事件。用户网站、公开 API、面试和桌面助手不依赖管理路由。

## 操作边界

- 积分与会员时长只允许追加调整记录，不允许覆盖余额。
- 支付对账不允许手工标记已支付；只有渠道权威通知可以发放权益。
- 支付宝订单重试会调用 `alipay.trade.query` 并验证渠道响应签名；未签名、状态未支付或金额不一致均不会发放权益。历史码支付订单在没有权威查询接口时只返回“不支持主动查询”，不会修改状态。
- 资料任务只允许调用既有重试流程，不允许直接编辑 OSS 或伪造可用状态。
- 用户封禁会撤销现有普通会话。
- 结束异常面试会同步关闭实时发布通道、重置服务端实时状态并将设备绑定标记为失效。
- 管理页面不展示简历、JD、知识库、转录、音频、截图和密钥原文。

## 服务器监控

“服务器监控”仅对拥有 `observability.read` 权限的管理员开放，每 15 秒刷新一次。资源卡展示后端容器 CPU、内存、所在文件系统磁盘、系统一分钟负载和可见运行时长；依赖卡分别探测 Backend、PostgreSQL、Redis、API 质量和运营分析任务。探针失败只将对应项标为“不可用”，不会阻断其他指标，也不会读取 Docker Socket、进程命令行或业务内容。

处理顺序：

1. 出现“异常”时先确认是哪一个资源或依赖触发，不要直接重启全部服务。
2. PostgreSQL 连接达到 70% 先关注、90% 为严重；先检查慢查询和连接泄漏。
3. 磁盘达到 75% 先关注、90% 为严重；只清理已确认可恢复的日志或构建缓存，禁止删除数据库卷。
4. Redis 或分析任务单项不可用时先核对对应容器和任务日志；用户 API 正常时可独立修复。

## 推广中心（本地开发，生产默认关闭）

推广中心使用独立的 `promotion.read`、`promotion.manage` 和 `promotion.cost.manage` 权限，提供推广总览、专属链接、营销活动、渠道比较和 Cohort 转化漏斗。渠道、活动、链接和成本变更写入现有管理审计；成本只允许追加和冲正，已产生有效访问的链接不能直接改写渠道或活动归属。

公开采集由 `OFFERSTEADY_PROMOTION_ENABLED` 控制，默认关闭。关闭时管理员会话不会获得推广权限，后台不显示推广入口，公开短链不设置分析标识。开启后访问和认领事件进入独立 Redis Stream，分析任务读取用户、面试和支付权威事实生成归因与快照；队列、任务或报表异常不得影响注册、下载、面试、ASR、快答、截图或支付。完整口径见 [推广中心数据口径与运行边界](promotion-center.md)。
5. API 5xx 或 P95 触发阈值时结合反向代理和 Backend 日志定位，监控接口自身不会计入请求质量窗口。

发布后至少观察一个 60 分钟采样窗口。需要回滚管理端时只回滚 Admin/Backend 镜像，数据库诊断列均为可空兼容字段，无需删除；Web 和桌面助手不参与本次构建。
