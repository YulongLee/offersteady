> 已合入后续笔试稳定性开发；当前待测试安装包见[同版本Local-r3](companion-1.3.6-local-r3-20261101.md)。本页保留r2历史证据。

# 伴随助手1.3.6：本地修订 r2

状态：源码修订、测试、三平台本地包及实际载荷核验完成，文件已放到本机下载目录。**仍为1.3.6；未获用户验收，不部署或更新官方分发。**

## 用户验收修订

- 移除首轮新增独立“重新检查”按钮、麦克风行包装和独立提示块，恢复既有界面。原麦克风行和错误区“重试麦克风”与封版逐字一致；隐藏短按钮保留。内部真实权限、晚授权、合并登记和模拟收音恢复修复保留。
- 隐藏主窗口与自身Dock/任务栏，菜单栏/托盘保留同一Tray、同一槽位，图像改为非空固定16×16逻辑尺寸的全透明位图及32×32的2倍表示。左击处理直接恢复原窗口和正常图像，右键仍能打开/退出。已有应用重开和快捷键恢复保留。
- 原正常图标SVG被Electron42.5.0读为空；以原绿底字形设计的PNG替换，恢复时使用真实非空图像。状态更新会保留当前透明态，不反复绑定事件。
- Mac隐藏时解除自动左键菜单绑定，右键用显式隐藏mainWindow宿主的Menu.popup；不走Tray程序化合成左击，不传全局屏幕坐标。Win保留原生右键菜单及幂等单/双击恢复。
- 显隐不改采集、绑定、心跳、音频状态、协议或网站。没有Backend/Web/国际服/正式助手分发更新，没有重新提交推送新助手。

## 已执行验证及限制

Desktop 47文件309项通过，主进程/Renderer类型检查通过；包验证工具19项通过，独立聚焦审查87项通过。原声学修复保持，无真实用户数据或模型/收费测试。

实际Electron42.5.0原生测试验证7项：正常/透明图像均非空且逻辑尺寸一致，两档透明像素全0；同一Tray边界隐藏前后均32×24且位置一致；隐藏宿主原生右键菜单不触发恢复；点击处理恢复同一窗口和正常图像；隐藏重建、快速显隐以最新意图为准。0线上请求、0麦克风请求，临时壳已退出。

**未将程序化事件当作物理点击。** 已尝试CUA指针点击，系统菜单栏位置因工具要求对应窗口而被拒绝；记录为工具限制。Mac实体原位左/右击和Windows/Intel实体音频仍需用户安装测试。原生边界、真实菜单和事件处理验证不能替代此验收。

## 本地安装测试

修订文件名含Local-r2，应用版本仍1.3.6，避免与首轮安装包混淆。默认仍连接现有国服HTTPS，不夹带测试地址覆盖文件或服务端密钥。

1. 先在旧助手中选择“停止并退出”，再安装本地r2包；没有替换本机Applications中的现用应用。
2. 检查界面无新增检查按钮；用自己的账号在国服测试原有功能与模拟面试。
3. 点击隐藏后，在原菜单栏/托盘图标位置左击恢复；右击检查打开/退出菜单。Mac可用⌘⇧H、Windows可用Ctrl+Shift+H或重新打开应用备用恢复。
4. 检查晚授权、设备切换、暂停/结束停止收音。测试未通过不发布。

Mac沿用相同Developer ID/bundle身份与音频权限，prepare-only签名，不上传公证；本地包仍未公证。Windows不宣称已通过Authenticode。硬件验收不包含在包字节核对中。

## 交付与证据

三包来自同一85份冻结输入，25份非native dist逐字相同；当前源与冻结输入逐hash一致，权限controller/coordinator及mock音频实现与首轮逐字相同。Mac两架构分别通过16份Mach-O实际签名/音频权限、原生载荷校验，DMG只读挂载后App逐文件一致。Windows外/内归档完整、x64实际载荷103份及25份dist一致，未执行Windows二进制。

下列文件位于`/Users/liyulong/Downloads/`，另有`OfferSteady-1.3.6-r2-本地测试说明.txt`；未替换Applications中的现用程序。Windows交付文件添加Local-r2别名，二进制与已验证安装包逐字相同。

| 平台 | 文件 | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| mac-arm64 | `OfferSteady-Companion-1.3.6-Local-r2-macOS-arm64.dmg` | 136389721 | `00178dec1b74c65fe49f95511cd32e911dfcac40cf3f99922aa1fb5d68b23df6` |
| mac-x64 | `OfferSteady-Companion-1.3.6-Local-r2-macOS-x64.dmg` | 141184220 | `1db6467c537d7aeed0ed76c5da093321bfbda22e52b28a0eba78f0117f93692f` |
| windows-x64 | `OfferSteady-Companion-Setup-1.3.6-Local-r2-Windows-x64.exe` | 102164665 | `70465907adb6e70828f2530e91ed9edd20e59c985618d8735b6d0b7124cff503` |

[三平台同源核对](companion-1.3.6-local-r2-20261101/cross-platform-source-verification.json)、[安装包路径](companion-1.3.6-local-r2-20261101/local-downloads.json)、[Mac ARM核验](companion-1.3.6-local-r2-20261101/mac-arm64-package.json)、[Mac Intel核验](companion-1.3.6-local-r2-20261101/mac-x64-package.json)、[Windows核验](companion-1.3.6-local-r2-20261101/windows-x64-package.json)、[原生测试及限制](companion-1.3.6-local-r2-20261101/native-window-smoke.json)、[独立复核](companion-1.3.6-local-r2-20261101/independent-review.json)、[生产作用域核对](companion-1.3.6-local-r2-20261101/scope-verification.json)、[UI原貌核对](companion-1.3.6-local-r2-20261101/ui-revision-review.json)。

完整本地构建/测试证据目录为artifacts/companion-1.3.6-local-r2/；首轮历史见[原记录](companion-1.3.6-local-20261101.md)。
