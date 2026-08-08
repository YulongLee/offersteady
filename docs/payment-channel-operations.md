# 官方支付渠道配置与上线验收

微信支付和支付宝的新订单配置由运营后台的“支付设置”管理。两种渠道可分别开启或关闭，也可同时开启。商户私钥、平台公钥和 APIv3 密钥使用 `OFFERSTEADY_ADMIN_ENCRYPTION_KEY` 派生的密钥加密后存入 PostgreSQL；后台只显示配置状态，不返回密钥原文。

## 上线顺序

1. 部署数据库迁移和应用，确认微信、支付宝均为“已关闭”。
2. 使用具有 `payments.manage` 权限并完成近期 MFA 验证的管理员登录。
3. 分别录入渠道配置并保存。配置修改会自动关闭对应渠道。
4. 只有校验状态为 `ready` 时才允许开启。可先单独开启一种，也可分别开启两种。
5. 每种渠道都先使用内部账号完成一次真实小额支付，再向普通用户开放。

## 微信支付配置

- 商户号、应用 AppID、商户证书序列号。
- 商户 API 私钥（PEM）、微信支付平台公钥（PEM）、32 字节 APIv3 密钥。
- Native 下单地址保持 `https://api.mch.weixin.qq.com/v3/pay/transactions/native`。
- 通知地址填写 `https://mianshiwen.cn/api/v1/billing/payment-providers/wechat/notify`，并在商户平台完成相应绑定。

真实验收需核对：Native 下单返回已验签、二维码可支付、通知签名和 AES-GCM 解密通过、商户与应用身份匹配、金额匹配、重复通知只入账一次、篡改通知不入账。

## 支付宝配置

- 应用 AppID、签约商户 PID。
- RSA2 应用私钥（PEM）和支付宝公钥（PEM）。
- 网关保持 `https://openapi.alipay.com/gateway.do`。
- 通知地址填写 `https://mianshiwen.cn/api/v1/billing/payment-providers/alipay/notify`。
- 返回地址填写 `https://mianshiwen.cn/app/billing`。

真实验收需核对：电脑网站支付已签约、官方收银台可打开、异步通知 RSA2 验签通过、应用与卖家身份匹配、金额匹配、重复通知只入账一次、返回页面本身不触发入账。

## 回滚与历史订单

关闭渠道只阻止创建新订单，不删除配置、订单、回调或账本。历史 MZFPay、支付宝和微信订单仍按订单保存的提供方隔离处理回调。发生异常时先在后台关闭对应渠道，再检查支付回调与对账事件；不得手工将订单改为已支付。

