# 商业管理后台运维

管理后台与用户端独立构建，默认关闭。生产发布数据库和后端代码不会自动暴露管理入口。

## 必需配置

```env
OFFERSTEADY_ADMIN_ENABLED=false
OFFERSTEADY_ADMIN_ALLOWED_ORIGINS=["https://admin.mianshiwen.cn"]
OFFERSTEADY_ADMIN_SESSION_TTL_SECONDS=1800
OFFERSTEADY_ADMIN_RECENT_MFA_TTL_SECONDS=300
OFFERSTEADY_ADMIN_SESSION_SIGNING_SECRET=<至少 32 字节随机值>
OFFERSTEADY_ADMIN_ENCRYPTION_KEY=<至少 32 字节随机值>
OFFERSTEADY_ADMIN_MAX_PAGE_SIZE=100
OFFERSTEADY_ADMIN_QUERY_TIMEOUT_MS=3000
OFFERSTEADY_ADMIN_RATE_LIMIT_PER_MINUTE=120
OFFERSTEADY_ADMIN_MAX_CONCURRENT_QUERIES=4
```

两个管理密钥只能进入服务器 Secret，不能提交 Git、写入 `VITE_` 变量或发送到浏览器。

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
