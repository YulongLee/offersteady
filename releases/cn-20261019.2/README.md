# 国服线上封版 cn-20261019.2

标签：[release-cn-20261019.2](https://github.com/YulongLee/offersteady/tree/release-cn-20261019.2)；分支 `codex/release-cn-20261019-2`。本版本从不可变的 `release-cn-20261019.1` 继承，封存已于2026年10月19日上线的笔试多屏回答；后续国服优化以本标签为起点。

笔试顶部新增默认关闭的“多屏回答”：开启后分别截屏、回答，最多4张按顺序统一处理一次。采集阶段不调用模型、不计费；关闭继续原单图流程。桌面全局快捷键仍走原单图，要累积多图使用网页按钮。

Backend 实际镜像 `sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88`；完整230运行输入逐SHA核对。Web 实际镜像 `sha256:011d1f5de69f1208bf8b9c5b9496d4acddcbe090e6c159a0173214eb8efbbee2`；完整328份公开静态原字节保存在 [web-static.tar.gz](web-static.tar.gz)，清单与包SHA见 [manifest.json](manifest.json)。封版前再次只读核对运行容器、230运行输入和328静态文件，见 [live-verification.json](live-verification.json)。

保留普通面试、模拟面试、简历v2及原PDF模板、会员简历每日3次/其他100积分、现有计费和性能优化。本次Git封版未操作线上服务，不涉及国际服、桌面助手、Admin、worker或数据库；生产私有配置、密钥及原始用户内容均不随Git保存。

[原发布记录](../../docs/releases/cn-written-multi-screen-20261019.1.md)保留首轮受保护恢复、第二轮成功及当时尚未Git封版的历史事实；[最终成功摘要](evidence/release-summary.json)、[独立验收](evidence/actual-verify.json)及[180秒脱敏观察](evidence/short-observation.json)只表示对应发布窗口。新增32项后端回归、598项Web测试、24项实际镜像离线ASGI检查、136项发布保护回归和15项编译Web检查此前通过；完整后端扩展回归存在已记录的旧失败/耗时波动，真实Windows/macOS桌面仍需用户试用。

## 恢复与继续开发

克隆并从本标签新建 `codex/` 分支，运行 `python3 -B scripts/verify_cn_current_release_snapshot.py` 核对230份运行输入、9份已发布前端增量源和328份静态包字节。原 `.1` 标签保持不可变，旧检查工具仍可在旧标签工作区验证历史版本。

前端封版基于上一版315静态文件加17份审核增量，原文件除4个HTML模块URL外保持，并增加13个hash资源；代码库里其余前端开发源码不能单独证明全量重建与线上等价。精确恢复网页应使用本目录静态包；继续修改前先核对 [编译覆盖清单](evidence/reused-overlay-manifest.json) 和实际镜像，不整包覆盖无关功能。`tools/web/` 保存当时的审核构建/验收脚本，脚本中的绝对路径是历史工作区，迁移使用时须先调整路径并重新核对全部SHA；它们不参与应用运行。

`tools/payload/` 保存最终受保护发布控制器和所需支持工具，`tools/fixtures/` 仅供合成保护回归；控制器绑定当时的容器、镜像和服务器目录，不能当作新发布授权或直接重跑切换。恢复应用文件不回滚用户资料、任务或账本。任何后续部署都需重新冻结目标来源和保护门禁。

本次封版额外补齐共享协议中的 `resume_optimizer_charge` / `resume_optimizer_refund` 类型声明，使既有简历账单页面可以在独立工作区通过类型检查；这两个账目类型已在线上使用，仅补齐编译声明，未改变230份运行输入或328份静态字节。封版工作区复核：32项笔试后端回归、Web类型检查、136项工具回归、当前快照校验和Spec严格校验通过。
