# 代码封版 20261104.1

版本标签 `release-20261104.1`，分支 `codex/release-20261104-1`，继承 `release-20261102.1`。保存今天已验收的两服实时性能优化和当前开发代码。国际服于2026-11-04 05:40:36上线后，再做本次Git封版；助手仍为 **1.3.6**。

| 组件 | 精确公开来源 | 状态 |
| --- | --- | --- |
| 国服Backend | `cn/backend-runtime.tar.gz`，237输入，a1e6固定镜像 | 国服今日三文件pin修复与此前共享阻塞/状态优化均已包含 |
| 国际服Backend | `global/backend-runtime.tar.gz`，307输入，457a固定镜像 | 今日独立Global适配已上线 |
| 国服worker/Web | 原`releases/cn-20261101.1/`的196/366输入包 | 新鲜只读确认保持 |
| 国际服worker/Web | 原`releases/20261102.1/global/`的267/251输入包 | 本次未更新，实际清单保持 |

完整六组件来源在[manifest](manifest.json)和[components](components.json)。两服收费、模型、语言、功能开关独立保留；国际服只同步本日适用的共享阻塞/pin/资料批读，不覆盖CN专属代码。发布记录：[国服](../../docs/releases/cn-pinned-binding-20261104.1.md)、[国际服](../../docs/releases/global-realtime-blocking-20261104.1.md)。

根目录还保留11月2日前已有、尚未上线的笔试网页/Backend配套，不能把根目录整仓构建视为线上等价版本；准确生产公开源码以各区域组件快照为准。Mac蓝牙收音本轮仅诊断，未修改助手或上线相关处理。封版不包含私有环境、用户音频/资料/原始标识或原始日志，不包含安装包和镜像层，不改变服务或账务。

## 离线核验与恢复

```bash
python3 -B releases/20261104.1/tools/verify_snapshot.py
python3 -B releases/20261104.1/tools/restore_snapshot.py --component global-backend --output ../offersteady-global-restored-20261104
python3 -B releases/20261104.1/tools/run_global_regressions.py
```

输出目录必须不存在。可选`cn-backend`、`cn-material-worker`、`cn-web`、`global-backend`、`global-material-worker`、`global-web`；工具只还原校验后的公开文件，不生成环境、不连接生产或恢复用户数据。Web是精确静态字节，不代表可从根目录重建。生产回退仍须重新验证私有冻结配置、固定镜像、归属和全部空闲门禁，不能直接重放本版本控制器。

Global已执行合成回归467项、发布及复用保护回归154项通过；真实Lua/大历史成本和限制见[evidence](evidence/regression-summary.json)与[规模证明](evidence/synthetic-scale-cost.json)。Global合成测试源码按三套保留于`global/tests/`；PostgreSQL需独占本地合成数据库，Redis需独占本地实例或测试自建进程，不得指向现有用户库。国服986项等历史实际结果保留于各自发布文档。本次Git快照工具和恢复验收见[verification](verification.json)。短时无新增5xx不等于高峰P95承诺。

后续从此不可变标签新建`codex/`分支优化；两服分别维护，不互相整包覆盖。
