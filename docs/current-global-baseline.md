# 当前国际服封版基线

用户于2026年10月22日授权将当前线上版本上传Git并封版。本版本标签为 [release-global-20261022.1](https://github.com/YulongLee/offersteady/tree/release-global-20261022.1)，分支 `codex/release-global-20261022-1`，继承独立区域基线 `release-global-20261019.1`。后续从此已确认不可变标签新建 `codex/` 分支；两服分别维护，不能相互覆盖。

| 组件 | 实际固定镜像 | 运行输入数 |
| --- | --- | --- |
| backend | `sha256:63f8243bacfc075cd399032ec5ca05f669356cd087b5d57583a9ce08b474e066` | 302 |
| material-worker | `sha256:dc8a809fce79291d15a127f8121fe7f87a3d1f51b3d77422aba81c569115890d` | 267 |
| web | `sha256:7f5fd6640aaea0b742eddb6227c41ddb7a0a0390fbe657486fdfef86efd38ad6` | 235 |

[封版内容和恢复说明](../releases/global-20261022.1/README.md)、[完整封版清单](../releases/global-20261022.1/manifest.json)及[新鲜只读核对](../releases/global-20261022.1/live-verification.json)保存实际组件来源。后端代码与独立资料worker分别完整保存；网页以封版静态包精确字节为准，普通全量源码构建不能自动视为线上等价。完整生产环境、端点凭据和镜像层不进入Git，仍留服务器。

Backend共享/快答/详答/截图4个模型选择器及旧worker共享选择器为 `deepseek-v4.1-flash-1017`。两组件分别在自身原镜像中仅增加摘要 `enable_thinking=false` 一行，原预算/回退保持。223条API、完整Schema、235份静态和Nginx保持。

保留英文及语言、Creem/原会员权益、简历UTC每日1次、普通/模拟面试原开关、默认关闭的笔试多屏、74个Prompt及鉴权/状态/心跳/预取/网页性能优化。ASR、TTS、Embedding、Rerank、MinerU不变。生产增量来源 `/opt/offersteady-global/releases/20261022-global-model1017-1`。

本轮封版只做源码、公开运行字节与脱敏证据的Git归档，不部署或重启线上，不修改用户资料、任务及账务。未来发布必须重新核对目标组件实际镜像、完整清单、有效配置及所有用户工作门禁；不能把标签目录或旧控制器当成新的部署授权。
