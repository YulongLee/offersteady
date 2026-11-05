# 代码封版 20261106.1

标签`release-20261106.1`，分支`codex/release-20261106-1`，继承`release-20261104.1`。保存两服已验收的用户作用域读取、准备/关闭隔离和ACK轻读优化，以及当前开发代码。国服01:22上线、国际服03:00上线后封版；本次同步不重启国服，助手均保持1.3.6。

| 组件 | 精确来源 | 输入数 |
| --- | --- | ---: |
| 国服Backend | cn/backend-runtime.tar.gz，1724固定镜像 | 238 |
| 国际服Backend | global/backend-runtime.tar.gz，687f固定镜像 | 308 |
| 国服worker/Web | 复用字节保持的releases/cn-20261101.1快照 | 196/366 |
| 国际服worker/Web | 复用字节保持的releases/20261102.1/global快照 | 267/251 |

完整来源在[components](components.json)和[manifest](manifest.json)。六组件均按实际运行来源核对，不把根目录源码当作全量线上版本。根目录仍含此前尚未上线的笔试配套，生产公开源码以区域快照为准，后续分别恢复对应组件后开发，不能CN整包覆盖Global。

本轮Global合成回归497项通过、0跳过，发布控制器与复用保护194项通过；真实独占Redis历史1/1242/10000验证命中无全站扫描、两列表共2往返/2解码，真实独占PG覆盖业务/资料/状态/模拟面试。实际镜像探针完整223Schema/379配置/46依赖和172编译通过。国服本轮1013通过/1项Global专属跳过及生产自测详见[国服记录](../../docs/releases/cn-cleanup-control-20261106.1.md)，Global真实部署/短时观察及限制见[国际服记录](../../docs/releases/global-cleanup-control-20261106.1.md)。短时无错误不等于高峰P95承诺；Mac蓝牙本轮没有修改。

## 离线核验和恢复

```bash
python3 -B releases/20261106.1/tools/verify_snapshot.py
python3 -B releases/20261106.1/tools/restore_snapshot.py --component global-backend --output ../offersteady-global-restored-20261106
python3 -B releases/20261106.1/tools/run_global_regressions.py
```

恢复目录必须不存在。可恢复cn/global的backend、material-worker、web六组件之一；Web为实际静态字节。工具只校验/恢复公开输入，不生成私有环境，不部署、不连接生产或恢复用户数据。Global测试源码和合成fixture分别在global/tests及global/test-fixtures；默认回归仅运行不需外部服务的业务测试，完整Lua/SQL测试需新建独占本机合成实例，不能指向用户库。

封版不包含密钥、私有环境/配置、原始用户资料/音频/会话标识/日志、安装包或镜像层。未提交的SEO研究目录不属于本轮代码变更，不纳入本版本。[脱敏验收与测试](evidence/regression-summary.json)、[规模证据](evidence/synthetic-scale-cost.json)、[Git封版工具核验](verification.json)。线上恢复必须重新核对全部空闲/归属门禁及固定镜像，不能重放旧控制器或中断用户。
