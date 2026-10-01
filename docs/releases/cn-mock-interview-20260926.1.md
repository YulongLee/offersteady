# 国服 AI 模拟面试发布 — 2026-09-26

## 范围与入口

仅国服网页和后端。用户授权先部署，随后自行真实设备测试。入口：`/app/mock-interviews`，侧栏位于笔试模式下方。兼容现有正式版 v2 麦克风助手，不发布新助手；国际服、后台站点、数据库/Redis/资料处理容器不切换。

创建/简历选择/机器码绑定、按简历与历史回答最多十题、女声 TTS 和头像播放声波、手动完成回答、报告与评分、两条自动保存记录。积分用户 100 分创建＋实际朗读/回答每开始一分钟 5 分；有效时间会员每日前三场免费，第四场起按积分收费。准备/生成等待/暂停/断线/报告不计分钟费。

## 验证与已知待验收

- 在实际国服基线上合并、重测：291 后端测试，55 前端测试，9 发布路由测试通过；生产构建和 Nginx 语法检查通过。
- 服务器真实百炼合成 TTS→ASR 首音频 0.559 秒、总计 11.48 秒，识别正确且连接关闭；九个 AI 场景结构检查及合成输出人工核对完成。无真实用户资料进入测试。
- **真实安装版助手的麦克风、耳机/外放回声、刷新重连及听感待用户测试**，不把合成回环当作真人验收。
- [完整验收与初跑问题记录](../../openspec/changes/add-ai-mock-interview/verification.md)。

## 基线与发布产物

发布目录：`/opt/offersteady/releases/20260926-cn-mock-interview-1`。

| 项目 | 标识 |
|---|---|
| 原后端 | `offersteady-cn-backend:answer-errors-20260925-1`，`01d093b2469e346ba6d68cd710f0ee7f3c5860bcedd0d0cc9a85e80fa803fc50` |
| 原网页 | `offersteady-cn-web:quick-stage-20260923-1`，`e20b47119c955b51d4df94daf6628033ff217f8b850dbb20e442831a1ecb3a21` |
| 新后端 | `offersteady-cn-backend:mock-interview-20260926-1`，`b74c3be657e0226f1542b554fd5e72d42353a15402f45053c07358928d08ba22` |
| 新网页 | `offersteady-cn-web:mock-interview-20260926-1`，`3dae5c374e157ab04d450ca1fb1e4168e582d976b295853de1d824c44cda02a2` |
| 兼容回滚后端 | `offersteady-cn-backend:mock-compatible-rollback-20260926-1`，`25e103c51b5581718460e46bb6cd9d6742f643b11c9c5a20c7efa28877088615` |

`backend-current`、`web-current` 指向本次目录；`current` 继续保留原编排/配置目录，不能据其源代码误判当前运行版本。以后发布应检查容器镜像及各组件的独立指针，不能整个脏工作区覆盖国服。

## 上线过程

- 多次门禁核查：live 面试、最近准备、页面租约、近期 ASR、未完成回答全为零。
- 在服务器本地保存并校验 `postgres-before-mock.dump` 及 `.env.production.before-mock`（限制权限，不下载或提交密钥/用户数据）。
- 迁移 `0051_mock_interviews.sql`：添加 mock 表、索引与扩展约束；现有会话/账本保留。锁等待 3 秒、语句超时 20 秒。
- 只增加 `OFFERSTEADY_MOCK_INTERVIEW_ENABLED=true`；其他容器环境逐项比较保持一致。
- 仅重建 `compose-backend-1` 和 `compose-web-1`。保留旧静态哈希资源，支持已打开页面继续加载旧资源。
- 公网健康、新路由、主页、管理员站点、支付状态、网页状态检查通过；未登录 mock API 为 401；新 WebSocket 通道拒绝无效认证。
- `/offersteady-build.json` 显示 `cn-mock-interview-20260926.1`；能力接口声明无需升级助手。
- 未修改普通回答模型、付款渠道、助手安装包和下载清单；未推送 Git。

## 回滚注意

发布目录保留 `deploy/switch.py` 和候选/回滚镜像。若需要回滚，先核查包括 mock 在内的活跃会话；恢复功能开关与旧网页，并使用上述**兼容回滚后端**，不要直接使用不认识 mock 记录的旧代码。保留数据库、已扣积分与免费次数，不执行删库、删除账本或自动还原旧数据库。

测试用隔离 PostgreSQL 和临时网页候选容器已停止；未清理历史生产镜像或用户文件。
