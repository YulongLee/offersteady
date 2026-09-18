# 国服客服微信更新

日期：2026-09-18（Asia/Shanghai）

国服客服微信已从 `mianshiwen-cn` 更新为 `mianshiwen_01`。国际服未修改。

## 更新范围

- 后端客服配置、默认值和 fallback。
- 国服首页、使用说明、联系页、用户协议和隐私页。
- 国服 SEO 联系页、前端测试夹具和回归断言。
- 保留客服邮箱 `contact@oneshowailab.com`。
- 历史审计快照和归档文档未改动。

## 验证

- API 测试：91 项通过。
- 后端支付/客服相关测试：11 项通过。
- 前端客服/使用说明相关测试：4 项通过。
- Web 与 API TypeScript 类型检查通过。
- `https://mianshiwen.cn/healthz`：HTTP 200。
- `https://mianshiwen.cn/api/v1/web/state`：`billing.support.wechatId` 返回 `mianshiwen_01`。
- `/`、`/contact`、`/terms`、`/privacy` 页面均返回 `mianshiwen_01`，未再返回旧账号。

全量 Web 测试仍有 7 项既有 SEO 基线失败，失败内容与客服账号替换无关；本次聚焦测试通过。

## 线上操作与回滚

- 仅重建并切换国服 Backend 和 Web 容器。
- 数据库、Redis、后台 Worker、Analytics 和 Admin 容器未重启。
- 原始配置已备份到 `/opt/offersteady/rollback/cn-support-wechat-20260918-192628/`。
- 如需回滚，恢复该目录中的文件后重新构建并切换 Backend/Web 容器即可。
