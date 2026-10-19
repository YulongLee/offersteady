# 当前国际服封版基线

用户于2026年10月19日授权将当前线上版本上传Git并封版。当前标签为 **`release-global-20261019.1`**，分支为 `codex/release-global-20261019-1`。后续国际服开发从此标签创建新分支；国服使用自己的独立封版。

- Backend：`sha256:f6a4dad4fb27222ca79f1fb5a86c23267093c741b4536c64ca76b83ac096ec19`
- Web：`sha256:7f5fd6640aaea0b742eddb6227c41ddb7a0a0390fbe657486fdfef86efd38ad6`
- 服务器发布目录：`/opt/offersteady-global/releases/20261019-global-written-multi-screen-3`
- [封版清单与恢复说明](../releases/global-20261019.1/README.md)、[新鲜只读核验](../releases/global-20261019.1/live-verification.json)
- [完整302项Backend清单](../releases/global-20261019.1/backend-runtime-manifest.json)、[235项Web清单](../releases/global-20261019.1/web-static-manifest.json)

本标签恢复实际已发布Global完整Backend与可证明的Global Web源码，不混入国服改写/模板回退或混合开发分支。英文、语言、Creem、原Global会员与模拟面试、简历UTC每日1次、鉴权/状态/预取/性能及74 Prompt保持；笔试新增默认关闭的多屏回答。桌面全局快捷键继续单图。

前端精确生产字节以封版静态包为准，使用其固定祖先和可移植overlay脚本可重建并验SHA。普通全量源码构建不能替代原静态保全证明。私有配置与密钥仅留服务器；未来发布先新鲜核对实际镜像与完整清单，活跃用户/未知状态停止切换。此次封版不部署或重启任何服务。
