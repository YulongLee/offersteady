# 当前国服封版基线

用户于2026年10月22日授权将当前线上版本上传Git并封版。本版本标签为 [release-cn-20261022.1](https://github.com/YulongLee/offersteady/tree/release-cn-20261022.1)，分支 `codex/release-cn-20261022-1`，继承独立区域基线 `release-cn-20261019.2`。后续从此已确认不可变标签新建 `codex/` 分支；两服分别维护，不能相互覆盖。

| 组件 | 实际固定镜像 | 运行输入数 |
| --- | --- | --- |
| backend | `sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88` | 230 |
| material-worker | `sha256:df6b8500500e955aa2f01c3bc0c5b40dab218296459f4e8341da268bb6b0ee43` | 196 |
| web | `sha256:407376001c127de09cbb93d6bd9ee5f30dcace2693eb0c60e51c22e27cc49c1f` | 328 |

[封版内容和恢复说明](../releases/cn-20261022.1/README.md)、[完整封版清单](../releases/cn-20261022.1/manifest.json)及[新鲜只读核对](../releases/cn-20261022.1/live-verification.json)保存实际组件来源。后端代码与独立资料worker分别完整保存；网页以封版静态包精确字节为准，普通全量源码构建不能自动视为线上等价。完整生产环境、端点凭据和镜像层不进入Git，仍留服务器。

Backend现有共享/快答/详答/截图4个模型选择器及worker既有3个文本模型选择器为 `deepseek-v4.1-flash-1017`。Backend与worker源未变；Web仅新增588字节上传代理规则，产品文件上限20MiB、三类资料请求封装21MiB，328份静态不变。203条API及完整Schema保持。

简历沿用10月18日v2和原PDF模板，时间会员每日3次、其余100积分；普通/模拟面试、默认关闭的笔试多屏、既有收费与性能优化保持。已撤回的v3–v6、新PDF研发版和国际服内容不得混入。ASR、TTS、Embedding、Rerank、MinerU、端点与Prompt均保留。生产增量来源 `/opt/offersteady/releases/20261021-cn-upload20m-model1017-2`。

本轮封版只做源码、公开运行字节与脱敏证据的Git归档，不部署或重启线上，不修改用户资料、任务及账务。未来发布必须重新核对目标组件实际镜像、完整清单、有效配置及所有用户工作门禁；不能把标签目录或旧控制器当成新的部署授权。
