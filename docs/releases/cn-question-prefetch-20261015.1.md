# 国服问题预取优化：生产发布记录

2026-10-15 **23:49（北京时间）**，在用户明确授权“将当前的代码部署到线上吧。我这边测试下效果”后完成国服 Backend 切换。发布目录为 `/opt/offersteady/releases/20261015-cn-question-prefetch-1`。

关联 [OpenSpec](../../openspec/changes/coalesce-cn-question-prefetch/proposal.md)、[本地验收](cn-question-prefetch-local-20261015.1.md) 和 [发布脚本](../../scripts/release_cn_question_prefetch.py)。用户可刷新 [国服页面](https://mianshiwen.cn/login) 测试，不需要安装新的伴随程序。

后续源码归档见 [20261016.1 Git 小版本](release-20261016.1.md)；门禁、probe 和纯合成切换测试保存在[发布支持目录](../../scripts/release_support/cn_question_prefetch_20261015/README.md)。

## 发布内容

只更新普通面试的后台问题预取：首段及时准备，中间连续更新合并为最新待办，最终问题优先；全局最多两个预取 worker。缓存绑定当前身份、完整问题和资料版本，旧任务不能覆盖新资料。会话清理及重置使用生命周期 token，防止旧观察任务重新入队。

用户点击回答仍不等待预取，详细回答仍独立检索。本次未更新 Web、Windows/macOS 助手、Global 或其它服务；字幕/音频协议、模型、Prompt、收费、模拟面试和已发布 heartbeat/ACK 优化保持。

## 实际运行与回退基线

| 项目 | 值 |
| --- | --- |
| 切换前实际 Backend Image | `sha256:eb242b56fded1473659c2f4517f07b42eeaff138b59029e5819fbaa972b12488` |
| 本次 Backend Image | `sha256:cc040a55f261a37226272c31937744e6ca4bd7a8c25e0810e360d218d41acfc0` |
| 本次容器 | `7e3ea04495bcaec9d8c072b892dcd86a87735af4ada2f002aaef92eae1039d25` |
| 本次镜像标签 | `offersteady-cn-backend:question-prefetch-20261015-1` |
| 回退镜像 | 上述切换前 `eb242…`，保留当前模拟收费与助手 1.3.5 清单 |
| 回退标签 | `offersteady-cn-backend:question-prefetch-rollback-20261015-1` |
| 当前基础 Compose | `/opt/offersteady/releases/20260923-cn-quick-stage-1/infra/compose/docker-compose.foundation.yml` |
| 本次私有 overlay | `/opt/offersteady/releases/20261015-cn-question-prefetch-1/compose.prefetch.json` |

发布前重新读取实际容器 Image 和全部 167 个 app/Prompt 文件哈希，与保存的实际国服基线完全一致；同时确认裸镜像中的业务文件与运行容器一致，不丢弃可写层业务变化。候选从实际镜像叠加已测试的三个文件，禁止使用混合工作区整包。

本次保留原环境文件、基础 Compose、共享 `compose-backend` 标签和源码目录指针；仅通过版本私有 overlay 将 Backend 指向固定镜像 ID。因此后续运维必须读取实际容器 Image、标签中的 Compose 文件顺序及私有 overlay，不能使用旧共享标签或健康版本字符串判断当前代码。

## 验证与切换保护

- 发布前重新执行实际国服源码候选的 **221 项相关回归 + 16 项回答流程测试**，均通过。原更宽本地检查中两个旧基线也存在的失败继续保留在本地验收记录，不作为已修复项目。
- 发布活动门禁合成回归 **122 项通过**；发布/自动回退/配置保护/日志脱敏回归 **36 项通过**，并经独立复核。发布脚本 SHA256 为 `41346a31fabd75718d907246ddd0f621df1c74b1686b00cb87302d432d14b91f`。
- 隔离候选容器使用 `network none`、只读文件系统及拒绝网络、DB、写文件、子进程、线程启动的 probe；未启动应用生命周期、未调用真实供应商或用户接口。
- 切换前连续复核五项只读活动门禁，普通/笔试 live、近期准备、页面租约、正在回答、桌面发布者、最近音轨、待处理截图、模拟面试进行阶段/有效 claim，以及资料任务的受保护计数全部为零。历史模拟场次仅 completed 30 条。7 条超过 24 小时且 durable job 已失败的旧 QUEUED 资料任务仅沿用既有例外，未修改记录。
- 仅对 Backend 执行 `--no-deps --no-build --pull never` 更新；原 IP 保留，不需要重载代理。其它 **7 个容器的 ID、Image 和启动时间保持不变**。
- 发布后及再次只读复核均通过：服务 healthy、重启次数 0；公网 `/healthz` 与 `/login` 返回 200；实际服务的 140 条业务 HTTP 路径与期望一致，两个模拟 WebSocket 路由保留。
- 实际新容器的 app/Prompt 全清单、177 个受保护方法、19 个路由模块、20 个 Prompt 和预取参数通过核对；环境变量、完整 HostConfig、挂载、有效模型/配置摘要保持。
- 短时启动日志观察：结构化 ERROR/CRITICAL、traceback 和 HTTP 5xx 均为 0。原始用户日志未导出。未执行独立数据库迁移、用户数据清理或真实面试创建。

实际候选的三个文件 SHA256：

- Chat：`8828c29018a1095899c7409123ab93dea33a00213fc58a51bd6afbf0e9ebe8cd`
- Realtime：`812d21e1019b92532f10b0c9c7bfe27839822157bcb1b6fbbccf34a54c154390`
- Scheduler：`36bc5ab7fc2329945a3becdedc0ccc0a38356c334e8b32a735610c58774d744f`

下载清单 SHA256 仍为 `76ba8b6009071d4c4c0b824b6bbbf1c05c7d848f95c1ab08649c9e9e05c4a76a`，助手 Windows/macOS 三个平台保持 1.3.5。国服会员每日免费一次、其余 100 积分一场和 60 分钟结束的规则保留。

## 运维证据与回退

脱敏证据保存在本地 `artifacts/cn-question-prefetch-20261015/release/production-*.json`；完整容器/环境/Compose 私有备份只留服务器发布目录，不导出密钥。

只读复核命令（服务器执行）：

```bash
python3 /opt/offersteady/releases/20261015-cn-question-prefetch-1/release_cn_question_prefetch.py verify
```

如用户后续要求回退，可运行同一脚本的 `rollback` 动作。它会再次检查活动门禁、发布归属、配置和镜像漂移，只恢复本次 Backend；若已出现其他发布则拒绝覆盖。本轮未触发生产回退；自动恢复分支通过合成测试验证。

## 效果边界

同负载合成检索 41→2、会话读取 41→3 证明重复后台工作下降，不能直接推算线上整体 P95。切换时无活跃面试，尚未完成真实负载下的 P95 改善验收，也未进行物理麦克风或真实模型效果验收。用户接下来测试字幕、点击回答与连续提问；客户端原有部分 question ID/revision 不匹配的缓存命中率限制仍见本地记录。
