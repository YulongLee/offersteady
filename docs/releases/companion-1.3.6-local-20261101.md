> 首轮本地包未通过用户外观/隐藏验收。当前修订见[同版本 r2 本地测试记录](companion-1.3.6-local-r2-20261101.md)；下列安装包与验收为历史首轮记录，不代表修订后行为。

# 伴随助手1.3.6：本地测试版

状态：**代码、回归、三平台本地安装包及实际载荷核验完成，文件已放到本机下载目录**。**不发布官网/OSS，不更新Backend/Web/国际服，不自动运行真实面试。**

用户要求先保存当前代码，已提交推送至 `codex/release-cn-20261101-1`，提交 `00d79ce2eb4f8281dfd434f25c47e8bd4dad4e9d`，远端标签 [release-cn-20261101.1](https://github.com/YulongLee/offersteady/tree/release-cn-20261101.1) 已核对。该封版助手仍1.3.5；新开发独立位于 `codex/companion-1-3-6-local`，新版本源码尚未提交推送。

对应 [OpenSpec](../../openspec/changes/improve-companion-permission-and-window-1-3-6/proposal.md)，核实问题见[权限排查](../diagnostics/cn-mock-permission-20261029.md)。

## 本次修改

- 主进程结构化读取真实OS麦克风权限，Mac授权单次在途；Windows不再无条件返回true。
- 界面2.5秒等待只表示待确认，继续接收晚授权；真实采集/新证据与卸载使旧查询失效，超时后仍可被动重检。权限变化即合并登记，失败复用既有控制周期重试，主进程15秒心跳不变。
- 识别mock后仅显示/检查麦克风；显式媒体探测结束立即停止所有流，普通电脑/手机/笔试策略保留。
- 模拟麦克风要求3秒内实际running；活动context挂起、track ended和持续mute（1.5秒宽限）使当前轮先隔离PCM，再有界释放并提示手动重试。100ms分帧、64KB上限、原重连退避保持。引擎错误不误报OS拒绝，旧socket/epoch/context/media回调不影响新轮。
- 点击“隐藏”收起主窗口、应用自身Dock/任务栏及菜单栏/托盘；再次打开应用或Cmd/Ctrl+Shift+H恢复同实例。恢复快捷键冲突时仍可用应用图标；托盘重建失败不挡主窗口。窗口重建与迟到Dock操作遵守最新显隐意图；重启默认可见，不修改采集/连接/截屏状态。
- 用户主动全隐藏明确调整历史桌面可见呈现要求，网页状态/停止及OS指示/权限提示继续保留，不保证投屏环境完全不可见。UI仅新增短按钮和必要错误/重试提示。

主版本/锁同步1.3.6，Electron42.5.0、稳定国服身份、协议、默认HTTPS地址保持。新增文案同时补充原copy生成门禁所需英文映射，未构建或发布Global安装包。

## 已执行验证

- Desktop **46文件303项通过**，主进程/Renderer类型检查通过。
- 独立6文件81项通过；包校验工具19项通过，包含未执行的合成Mach-O重签载荷对照。
- 旧封版MockMicrophone复现3项新回归失败，新实现均通过；mock专用35项覆盖相关分支。
- 使用实际Electron42.5.0及编译后的窗口controller、独立userData验证6个原生窗口/Dock/Tray场景：全部隐藏、同窗口恢复、隐藏重建、恢复重建窗口、快速意图切换。快捷键可注册，未模拟实体按键；无麦克风/线上请求、未登录账号，测试壳已退出。
- 独立审查推动修正托盘重建失败影响恢复、超时旧waiting挡新重检两个边界；未放宽断言。初次全量检查仅版本测试仍期待1.3.5，已更新为新版本精确1.3.6；新文案补齐原翻译门禁后全量通过。

证据位于 `artifacts/companion-1.3.6-local/`。物理Win/Intel音频、蓝牙与完整真实线上会话仍需用户对应设备测试；合成测试和包结构检查不替代硬件验收。

## 安装与测试安排

本地包默认连接 `https://mianshiwen.cn/api/v1` 及 `https://mianshiwen.cn/app`，不放loopback-only的local-test-runtime或Global配置，不含服务器密钥。正式官网助手继续为1.3.5。

1. 在旧助手菜单中选择“停止并退出”，仅关闭窗口会保留旧进程。
2. 安装对应架构本地包，确认界面为1.3.6，用自己的账号在国服绑定测试。
3. 优先检查麦克风晚授权/重检、模拟面试回答转写、隐藏/恢复、耳机切换，以及网页暂停/结束后停止收音。
4. 隐藏后可再次打开安装的应用，或按Mac `⌘⇧H` / Windows `Ctrl+Shift+H` 恢复；没有新增可暴露在投屏中的悬浮入口。

Mac采用既有Developer ID签名prepare-only，不上传公证；保留真实未公证状态，不关闭系统安全保护或重置隐私授权。Windows不宣称Authenticode已验证。两个Mac分别通过16份Mach-O实际签名、主/4份Helper/native音频权限及各自架构检查；本地DMG只读挂载后整个App逐文件/链接与已验证App一致。Windows外层NSIS与内层app-64.7z均通过完整性检查，真实x64载荷102份文件及24份dist精确保持，未执行Windows二进制。


## 本地交付

三包来自同一84份冻结源输入，24份非native dist逐字相同；Mac额外各含匹配架构的Swift采集程序，Windows不混入Mac native。版本1.3.6与国服默认地址、稳定应用身份保持，无local-test/Global覆盖文件或服务器凭据。

| 平台 | 下载目录文件 | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| Mac Apple Silicon | `OfferSteady-Companion-1.3.6-Local-macOS-arm64.dmg` | 136552266 | `a010befb20f531f5d0f50f91e54079ef67cf38da47b9f15d3c55b0c32143563c` |
| Mac Intel | `OfferSteady-Companion-1.3.6-Local-macOS-x64.dmg` | 141182902 | `0177aa408644f6eb9065f35edab02083e3e92ce06e63a9f46ac6da48515794e7` |
| Windows x64 | `OfferSteady-Companion-Setup-1.3.6-Windows-x64.exe` | 102160617 | `1689ea998ef4d39fea069160a092aecaf709fee6cfd3acc821f9f2fe703d51fc` |

文件均位于 `/Users/liyulong/Downloads/`，另附 `OfferSteady-1.3.6-本地测试说明.txt`。没有替换Applications中的现用程序或启动真实收音，安装由用户在退出旧版后完成。

Intel载荷初次校验发现签名器增加8个零填充并改变LINKEDIT派生大小；已保留原编译文件及旧清单，验证代码/数据/UUID/其他加载命令逐字一致，只规范签名16字节对齐及派生大小。新expected仅取自原编译载荷，未从签名成品反设；工具ARM/Intel实物格式回归19项通过，原ARM摘要保持。无产品代码变化或重新打包掩盖漂移。

[Apple Silicon检查](companion-1.3.6-local-20261101/mac-arm64-package.json)、[Intel检查](companion-1.3.6-local-20261101/mac-x64-package.json)、[Windows检查](companion-1.3.6-local-20261101/windows-x64-package.json)、[独立审查](companion-1.3.6-local-20261101/independent-review.json)、[原生窗口演练](companion-1.3.6-local-20261101/native-window-smoke.json)、[作用域核对](companion-1.3.6-local-20261101/scope-verification.json)、[本地交付路径](companion-1.3.6-local-20261101/local-downloads.json)。
