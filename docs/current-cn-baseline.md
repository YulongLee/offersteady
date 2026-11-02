> **2026-11-02国服助手1.3.6三平台下载已发布。** 仅热更新Backend内下载清单，业务容器及代码未重启/替换。新清单SHA为`d7b106a6497bce873d67c2c81b045fab520aaa7382296978a8f6a04056e10927`；实际Backend仍为下述c62df镜像，其镜像内旧清单与运行可写层不同。未来重建必须显式携带新清单，或使用仅增加清单的固定镜像`sha256:15824dc57cdaaa817d171f11e3750cc84919750259a595c4741b042bbb2129ab`及专用覆盖材料。见[发布、验收及恢复说明](releases/companion-1.3.6-cn-20261102.md)。国服Web/Backend笔试配套仍未部署；国际服已独立完成[性能与助手更新](releases/global-performance-companion-1.3.6-20261102.md)。当前代码与两服公开运行文件封存为[release-20261102.1](../releases/20261102.1/README.md)，原控制器不能直接重放。

> **2026-11-01国服模拟面试修复已上线。** 实际Backend为 `sha256:c62df7ddbb92627de83c7c2733574c862678b120a11d051b346b9d13abfcf58a`（232份输入），实际Web为 `sha256:4586bab84a0c18b4aadba9e9be079960372abdc6334030c01f59dbb45bffff76`（366份公开文件，入口 `assets/main-48f3fcb5.js`）。仅CN Backend/Web模拟面试最小增量，保留此前SEO、状态/控制查询优化及全部旧资产，池关闭、worker不变。用户随后授权Git封版 `release-cn-20261101.1`，见[封存清单](../releases/cn-20261101.1/README.md)，该封版时助手为1.3.5。后续以实际组件及此标签作为业务开发基线，不使用旧目录或整包源码构建覆盖生产。

11月1日基于10月29日实际Backend `sha256:3e56917daba635e780d9bd728694d823494b40a6ab67a9968c5371c1378abb3e`（231输入）及Web `sha256:99822e10e7b516aefe4ad96248f9eea631d90b057cb77b8dd386cff4830516fb`（353公开文件）叠加五个mock Python文件及专用页面/播放器/样式。完整203条API Schema、有效配置、44依赖、普通/笔试/简历功能、模型/计费/截止时间、Nginx/CSP和六个非目标保持。Web兼容回退为 `sha256:1d082083d495c6078efcd04006409e0b4c33486a16d703b8b099fb4fe1405775`，包含全部旧字节与13个新资源。新发布没有Git提交/推送。

10月29日是在已上线的[10月27日SEO资源图](releases/cn-search-content-20261027.1.md)及原实际Backend镜像上叠加最小增量，不能用旧封版或完整本地源码构建整体覆盖当前网页。模拟面试、简历优化、多屏、收费、模型、助手、SEO/CSP及六个非目标组件保持，无数据库迁移或Git提交推送。

# 最近国服Git封版基线

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
