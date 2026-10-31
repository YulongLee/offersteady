# 国服封版 cn-20261101.1

标签 `release-cn-20261101.1`，分支 `codex/release-cn-20261101-1`，继承 `release-cn-20261022.1`。用户要求先保存当前代码，再开发伴随助手1.3.6；本封版的助手仍为1.3.5，不包含新的隐藏/权限修复。

本次以真实运行组件再次只读核验，不部署、不重启、不调整用户数据或账务。当前生产包含10月27日SEO、10月29日状态/控制查询减负及11月1日模拟面试权限/播放/ASR清理增量；连接池保持关闭。详见[生产发布记录](../../docs/releases/cn-mock-20261101.1.md)。

| 组件 | 实际固定镜像 | 封存内容 |
| --- | --- | --- |
| Backend | `sha256:c62df7ddbb92627de83c7c2733574c862678b120a11d051b346b9d13abfcf58a` | 仓库232份运行输入，完整逐SHA清单 |
| material-worker | `sha256:df6b8500500e955aa2f01c3bc0c5b40dab218296459f4e8341da268bb6b0ee43` | 独立196份实际运行输入及原字节包 |
| Web | `sha256:4586bab84a0c18b4aadba9e9be079960372abdc6334030c01f59dbb45bffff76` | 实际366份公开静态文件完整包及Nginx |

普通面试、快答、笔试多屏、简历v2与原PDF、现有计费和模型保持。Web不等同整仓源码重新构建的dist；worker不等同当前Backend。生产环境、端点凭据、容器镜像层、原始用户资料及日志不进入Git。

在本标签检出目录执行 `/Users/liyulong/anaconda3/bin/python -B releases/cn-20261101.1/tools/verify_snapshot.py`，离线核对源码、worker/Web归档、Nginx及203条完整API Schema。使用 `restore_snapshot.py --component backend|material-worker|web --output <空目录>` 可还原对应文件，不调用Docker、不恢复用户数据、不发布线上。

`live-verification.json`为此次新鲜只读回执，`manifest.json`固定全清单、来源及摘要。真实运行镜像及私有配置继续留服务器；恢复部署需另行授权、重新核对组件归属和在线用户门禁。开发/发布测试结果及历史2项TTS测试失败见上述生产记录，封版本身不代表真实硬件端到端验收。
