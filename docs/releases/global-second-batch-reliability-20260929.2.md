# 国际服第二批可靠性优化 — 2026-09-29

## 发布范围

版本 `20260929-global-reliability-2`，基线为国际服实际运行的第一批 Backend/Web，加上各自仍在运行的旧 Admin 和 Material Worker。约北京时间 13:31 切换，仅重建这四个组件；国服未操作，PostgreSQL、Redis、Analytics 容器身份及环境哈希保持不变。没有数据库迁移。

1. **PDF / 简历处理**：Worker 不再把已安排重试的解析任务覆盖成失败。资料页最多查询 45 次，完成或失败立即停查，超时提示后台仍在处理；离开页面取消请求，迟到的重试响应也不再开启轮询。
2. **回答清理**：回答流提前关闭时关闭底层迭代器、取消未完成任务，按既有规则释放预留和自动回答占用。保存已生成内容，拒绝迟到结果将取消状态重新写成生成中、完成或失败。正常完成不额外取消。同步供应商 I/O 仍受既有超时约束，不承诺瞬时中断。
3. **国际服后台会员管理**：邮箱/昵称/用户 ID 搜索，每页 30 条；列表和详情显示明确 UTC 注册时间。拒绝过期搜索与详情响应；确认框显示准确身份和目标权益。防止并发重复操作，同页面相同操作的失败重试复用幂等键；操作成功但刷新失败时只引导刷新，不再重复赠送或撤销。

不包含联网回答、模拟面试、模型/Prompt 更换、国服积分规则、音频策略、桌面助手升级或磁盘清理。国际服 10 种语言、邮箱认证、Creem 和会员套餐保持原实现。

## 测试证据

| 检查 | 结果 |
| --- | --- |
| 隔离 Global 后端回归 | 76 通过，1 项 PostgreSQL 集成因未配置独立测试数据库跳过 |
| 修复前后对照 | 旧基线上新后端回归 8 失败、10 通过、1 跳过；修复后专项及第一批回归 25 通过、1 跳过 |
| 后台旧响应竞态 | 旧基线实际选中第二人却向第一人发命令，合成测试复现；新版本通过 |
| Global Admin 全量 | 72 通过 |
| Global Web | 111 通过；3 项既有断言失败单列后跳过，不宣称全仓全部通过 |
| 构建 / 类型 / 文案 | Web 与 Admin 生产构建及类型检查通过；Global 文案审核通过 |
| 浏览器 | 正式 Admin 包在 1440 / 768 / 390 宽度验证搜索、分页、详情与横向布局；使用合成用户，不调用生产 API |
| 实际镜像离线冒烟 | 无网络验证 Worker 重试、SSE 断线取消与容量释放、简单阶段顺序、启动拒绝、Global 权益、认证路由和 10 种语言；两份 Nginx 配置通过 |
| OpenSpec | `sync-global-second-batch-reliability` 严格校验通过 |

既有 Web 断言：`HomepageFeedback` 的静态评价、`global-product` 的评价位置、`public-commercial-disclosures` 的旧 v2 目录文案。第一批已记录相同问题，不属于此次改动。

主工作区仍包含国服联网等变更，**不得将主工作区 Backend 整包发布到国际服**。主工作区跑 Global 预留集成时曾复现国服额外计费参数不兼容，因此两项 Global 专属集成在该工作区明确跳过；在隔离 Global 发布候选里两项均实际通过。生产镜像没有引入这些国服参数。主工作区本轮其他新增专项：后台 19 通过，资料页 8 通过，后端 8 通过 / 2 个 Global 专属场景跳过。

没有在生产创建测试用户、面试、订单，未修改真实用户权益或调用付费模型。真实设备体验仍需要上线后验收。

## 上线门禁与核验

最终门禁时间戳 `1790659867856`：进行中面试、近 5 分钟准备、有效面试页租约、近 30 秒活跃音频、未完成回答任务及运行中的解析任务均为 0。

- 当前目录 `/opt/offersteady-global/releases/20260929-global-reliability-2`。
- 所有容器环境变量哈希保持不变；四组件命令、工作目录、内存/CPU 配额、端口、日志配置和重启策略与原运行值一致。
- Backend 仅覆盖 4 文件；Worker 从其自身旧镜像仅覆盖 `commercial_worker.py`，没有从新 Backend 全量重建。
- 首页、应用、登录、Admin 可访问；Web/Admin 入口资源和资料页模块字节校验匹配。
- 配置、认证依赖、语言注册表、回答模型服务、Global 计费/支付实现、助手发布清单与父镜像哈希一致。
- Creem 仍为 live / enabled / ready；5 项目录规范化 SHA256 仍为 `3c082fd29ec1f9ea523ee56351f75d02ceb13845f9c9afb6ae99dcefbc41b924`。
- Windows x64、macOS arm64/x64 的既有 1.3.2 下载 Range 核验通过，未更新助手。
- 上线窗口首次核验无 Traceback 或 ERROR 日志；这不代表长期零故障保证。
- 后续复核 Backend 已转为 healthy，Backend/Worker 重启计数均为 0；运行配置及资源校验再次通过。磁盘约 85%，可用 7.5 GiB，本轮没有清理旧发布或镜像。

## 镜像与回退

| 组件 | 新镜像 SHA256 前缀 | 新标签 |
| --- | --- | --- |
| Backend | `c45cd105965c` | `offersteady-global-backend:reliability-20260929-2` |
| Material Worker | `73624b44e619` | `offersteady-global-material-worker:reliability-20260929-2` |
| Web | `399857ca5473` | `offersteady-global-web:reliability-20260929-2` |
| Admin | `c094f39b2a03` | `offersteady-global-admin:reliability-20260929-2` |

四组件原镜像分别保留为 `offersteady-global-<service>:baseline-20260929-2`。旧版本目录与镜像未删除。部署脚本带失败回退，本次未触发回退。

必要时先确认空闲，再执行：

```sh
cd /opt/offersteady-global/releases/20260929-global-reliability-2
docker exec -i -w /app/apps/backend offersteady-global-backend-1 python - < deploy/check-idle.py
# 只有门禁成功后才能继续：
docker compose -p offersteady-global --env-file .env.global.production \
  -f infra/compose/docker-compose.global.yml -f deploy/compose.rollback.yml \
  up -d --no-build --no-deps backend material-worker web admin
ln -sfn /opt/offersteady-global/releases/20260929-global-reliability-1 /opt/offersteady-global/current
```

运行环境覆盖文件只保存在服务器，权限 0600，含既有运行凭证，不应复制到仓库或本地。其余无凭证源代码、测试、构建、浏览器截图和发布日志保留在 `artifacts/global-second-batch-20260929/`。本轮未提交或推送 Git。
