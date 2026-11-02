# 伴随助手1.3.6：笔试截屏稳定性本地修订r3

后续状态：Desktop部分已于2026-11-02正式发布国服，见[正式发布记录](companion-1.3.6-cn-20261102.md)；Web/Backend配套仍在本地。以下保留11月1日本地交付时的原始记录。

状态：开发、自测、独立复核及三平台本地安装包核验完成，文件已放到本机下载目录。**版本仍1.3.6；未部署、未更新官方下载/OSS、未推送Git。**

用户授权将笔试连接、截屏恢复及失败提示合入当前测试版，后续统一上线。继承[Local-r2](companion-1.3.6-local-r2-20261101.md)外观、真实权限/模拟收音修复、透明可点击Tray。依据[只读诊断](../diagnostics/cn-written-screenshot-20261101.md)，规范见[本轮OpenSpec](../../openspec/changes/stabilize-written-screenshot-local-1-3-6/proposal.md)。

## 修改内容

- 心跳完整操作8秒期限、15秒正常节奏、2秒合并恢复；系统恢复/窗口前台/网络online触发当前状态刷新。晚到身份读取、响应、旧连接及旧场次不覆盖新轮。仅已有同场服务器绑定验证通过后唤醒暂停的截图流，不自动新建/重绑面试或开收音。
- 有效live笔试期间短时可续期prevent-app-suspension；丢失资格/45秒未续期/退出释放，隐藏不弹窗口，不锁定显示器。原生Mac验证实际OS保护能开始、隐藏时保留、结束释放；不宣称已证明用户断档由App Nap引起。
- 笔试截图1active+4pending FIFO，128项跨重连代际的请求去重，60秒排队和服务器旧请求时限；捕获10秒、上传30秒及检查/报告有界。前后同场请求校验、owner锁租约、SSE generation、取消/旧结果隔离。不自动重传上传或重复模型/计费；不可中断的OS屏幕读取未结束时不启动更多底层读取，晚结果不能上传或释放新锁。普通分支保持，锁释放仅增加owner保护。
- 现有Backend next读取增加可选sessionId/requestId。仍用设备凭证校验当前live绑定和owner/session/device/code，指定请求可返回取消/处理中等终态；无参数旧分支保持。无写入/claim/锁/模型/计费；只有一个Backend运行文件变化，其余231份逐hash不变。
- Web仅笔试现有失败入口区分离线/绑定失效/捕获/上传；单屏与快捷键旧回调不覆盖新结果，多屏失败保留已收图片。无新常驻文案、检查按钮或布局。
- r2权限controller/coordinator、mock音频类、窗口/Tray模块、隐藏按钮及样式逐字保持。编译排除main源目录内历史回归测试；完整测试现已实际覆盖它们，包检查额外拒绝运行时测试文件。无依赖/原生采集程序/签名身份/协议版本变化。

## 自测

- Desktop 54文件394项通过，main/renderer typecheck和构建通过。
- Backend 5组92项通过（含新增scoped read34项），Web7组148项通过及typecheck。
- 独立实际main函数提取36项、相关桌面89项及Backend34项通过；发现的跨场取请求、补查空转、旧检查释放新lease、旧SSE owner和普通旧finally释放新锁均已修正，不放宽断言。
- Backend新GET操作除sessionId/requestId两个可选参数外与封版Schema逐字一致；同模块其他AST保持，232运行输入仅该模块变化。没有运行app lifespan、生产查询、模型或账务测试。
- 实际Electron42.5.0隔离壳9个检查通过：非空两档透明图像、同一Tray及原生边界、原生菜单/窗口恢复、隐藏重建/快速意图，以及真实OS app-suspension保护的持有/释放。0线上/麦克风请求。菜单栏物理指针操作仍受CUA限制，不把程序化事件称实体点击；临时壳已退出。
- Web合成本地预览验证助手离线→原按钮重试、上传失败、取消首请求后新请求成功且6秒后旧409不覆盖。构建只过滤会读取线上pricing的插件，并显式禁外网，未改pricing配置；产物不当作线上等价全站包。
- 最终去重/原生读取边界修订后重新执行完整回归并完整重建Mac候选，初轮候选保留内部证据而不作为最终交付。

包验证工具20项通过，含拒绝误编译测试进入安装包。早期验证发现20项新回归误放main源目录，已迁入test并加入全量；两项历史main测试也纳入全量且排除编译，未交付含本轮测试的r3包。

## 如何本地测试

新文件名含Local-r3，应用内版本仍1.3.6。先完全退出旧助手，再装对应架构测试包；本次未替换本机Applications中的现用应用。

助手默认连接现有国服HTTPS，可先测试新场次笔试中的连续截屏、取消重试、短时断网恢复、隐藏/恢复及原模拟收音。**Web/Backend配套仍仅本地**：旧国服会忽略新查询参数，助手会强检验其返回值；同场正常请求可兼容，跨场旧pending完整隔离需后续统一发布配套。旧场次异常时明确保守放弃，不截错页面。

完整本地Web反馈演练入口：[本地笔试预览](http://127.0.0.1:5184/test-previews/written-multi-screen.html?scenario=assistant-offline)。scenario还可选binding-invalid、capture-stage-error、upload-stage-error、cancel-late-error，均为合成画面/内存操作，不访问线上或扣费。构建/浏览器验证方式见[Web验收](../../openspec/changes/stabilize-written-screenshot-local-1-3-6/web-verification.md)。

Windows/Intel实体设备、真实Mac网络断档/休眠及完整线上面试仍需用户验收；现有证据不保证所有网络/OS故障消失。Mac本地包沿用Developer ID与bundle/team/audio权限，未上传公证；Windows不宣称Authenticode已验证。

## 交付证据

三包88份冻结源输入完全相同，26份非native dist逐字一致；当前源逐hash匹配冻结输入。Mac两架构各通过16份Mach-O实际签名/音频权限、架构及原生载荷校验；DMG只读挂载后App逐文件一致。Windows外/内归档完整性、实际x64载荷104份及26份dist全部匹配，未执行Windows二进制。

所有交付文件位于`/Users/liyulong/Downloads/`，另附`OfferSteady-1.3.6-r3-本地测试说明.txt`。

| 平台 | 文件 | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| mac-arm64 | `OfferSteady-Companion-1.3.6-Local-r3-macOS-arm64.dmg` | 136474299 | `108f8340e18a75abc73a08c752c4c58d11dfcab997d7be41f0e3f84f71a240b1` |
| mac-x64 | `OfferSteady-Companion-1.3.6-Local-r3-macOS-x64.dmg` | 141188744 | `ed124fac10c4188f8e5fa98bd3b7300654c7f8c9f2d4ae9596b93e26d69e7a3b` |
| windows-x64 | `OfferSteady-Companion-Setup-1.3.6-Local-r3-Windows-x64.exe` | 102172270 | `18fd93b8d8c2ff412c0baea7a728eb392ba70962bae96a1f5bb27224ab811f54` |

[本地交付路径](companion-1.3.6-local-r3-20261101/local-downloads.json)、[三平台同源核验](companion-1.3.6-local-r3-20261101/cross-platform-source-verification.json)、[ARM包核验](companion-1.3.6-local-r3-20261101/mac-arm64-package.json)、[Intel包核验](companion-1.3.6-local-r3-20261101/mac-x64-package.json)、[Windows包核验](companion-1.3.6-local-r3-20261101/windows-x64-package.json)、[独立复核](companion-1.3.6-local-r3-20261101/independent-review.json)、[原生窗口和Power验证](companion-1.3.6-local-r3-20261101/native-window-smoke.json)、[Backend合同](companion-1.3.6-local-r3-20261101/backend-contract-verification.json)、[r2保留核对](companion-1.3.6-local-r3-20261101/revision-source-comparison.json)、[配套源指纹](companion-1.3.6-local-r3-20261101/local-server-web-inputs.json)。

完整本地证据目录：artifacts/companion-1.3.6-local-r3/。生产服务与官方下载继续原版本。后续统一发布应重新核对实际Backend/Web运行镜像并做最小增量，不能把本次合成源码build当成生产整站包。
