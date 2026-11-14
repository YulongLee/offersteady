# 国服伴随程序 2.0.0 本地候选

状态：已完成三平台本地候选封装，Mac 两架构 App 与 DMG 公证和只读挂载核验通过；未上传、未部署或修改线上下载入口。三平台仍有真实场景验收缺口，不得视为已完成正式发布。

## 制品

| 平台 | 制品 | SHA-256 | 事实状态 |
| --- | --- | --- | --- |
| Mac Apple Silicon | `artifacts/cn-companion-2.0.0-candidate-r2/OfferSteady-Companion-2.0.0-macOS-arm64.dmg` | `99eeea79ef001e37c1347e8c87493291177973db83ded048f33421966904bbad` | Developer ID 签名、App/DMG 公证与票据、Gatekeeper、只读挂载载荷及架构检查通过 |
| Mac Intel | `artifacts/cn-companion-2.0.0-candidate-r2/OfferSteady-Companion-2.0.0-macOS-x64.dmg` | `8cdfbf524ce8abf0763a7e28c8d647781405deb5f0574412624f4f857527b27f` | Developer ID 签名、App/DMG 公证与票据、Gatekeeper、只读挂载载荷及架构检查通过；未进行 Intel 真机验收 |
| Mac Apple Silicon | `artifacts/cn-companion-2.0.0-candidate-r2/OfferSteady-Companion-2.0.0-macOS-arm64-Signed-Not-Notarized.zip` | `6fdad2d4da7bb3ccf53696951fb70d8a8fba3a8fd0906300233af8dc45ffba1d` | Developer ID 签名及架构检查通过；未公证，仅供预审，不是正式发行包 |
| Mac Intel | `artifacts/cn-companion-2.0.0-candidate-r2/OfferSteady-Companion-2.0.0-macOS-x64-Signed-Not-Notarized.zip` | `4d97a122dd342151b5ad3f7bf888bada6d2eb547757fb29eb9a2fe8c061cb9d6` | Developer ID 签名及架构检查通过；未公证，仅供预审，不是正式发行包 |
| Windows x64 | `artifacts/cn-companion-2.0.0-candidate-r2/OfferSteady-Companion-Setup-2.0.0-Windows-x64.exe` | `2ca70baa786662c176d2a3d78831e5c1029a1369dfd68e15d799dbb5346a8af8` | NSIS 本地候选，构建时未配置 Windows 签名；已独立复核包内容，尚待真实 Windows 验收 |

两份 Mac ZIP 为此前 App 签名预检，不能替代已生成 DMG 的 App 与 DMG 双公证、staple 和 Gatekeeper 验收。此前 Apple Silicon App 公证尝试失败，`notarytool history` 返回 HTTP 403，提示团队所需协议缺失或过期；用户处理账号后重新提交，两架构 App 与 DMG 均获 Accepted 并完成票据附加。最终 DMG 只读挂载后，各架构内 App 的 286 个文件及链接与公证后封装源逐项一致，App 签名及票据、DMG 票据、Gatekeeper 和架构均通过。证据：[四项公证回执](../../releases/20261115.1/evidence/notary-submissions.json)、[Apple Silicon 挂载核验](../../releases/20261115.1/evidence/arm64-mounted-verification.json)、[Intel 挂载核验](../../releases/20261115.1/evidence/x64-mounted-verification.json)。

## 输入和验证

三平台从本地留存的国服 1.3.6 已发布安装包构建，按已封版清单校验文件大小及 SHA-256；沿用测试版的精确增量和反向还原校验。Mac 候选每架构 129 个原应用文件字节保持，包括四个原渲染文件；Windows 候选 25 个原应用文件字节保持，包括四个原渲染文件。Windows 安装包重新解包，候选载荷逐文件比对通过；Windows 可执行文件架构由构建器检查。独立解包核对 Windows 104 份旧载荷文件没有缺失，仅 EXE、package 元数据、入口 index 变化，新增 9 个浮窗和标志文件；正式标志、标题状态及四个浮窗主进程模块与最终构建一致。该检查不代表真实 Windows 运行验收。

正式候选通过包内标志启用原正式数据目录及旧目录迁移，未标志的测试构建仍使用独立测试数据目录。合成升级测试覆盖正式设备身份与凭证存在时不得被旧数据覆盖，不读取真实设备数据。正式候选浮窗不显示“国服测试”标签，测试候选保留该标签。

桌面类型检查、浮窗类型检查和浮窗构建通过。直接运行 Vitest 全量 57 个文件、410 项通过；其中包括合成设备身份、截图和浮窗测试。标准 `npm test -w @offersteady/desktop` 未通过其前置国际服文案生成步骤：浮窗相关七条中文缺少英文映射；这不是全套 npm test 通过。未在本次调用真实模型、真实会话或支付。

## 限制

本机 macOS 音频授权和真实线上业务链路未对最终 r2 安装包重新验收，Windows 未在真实设备运行或确认音频、身份迁移和会议接收端。用户此前在当前测试环境反馈腾讯会议、钉钉、飞书正常；Zoom 共享与录制仍显示浮窗。第三方共享/录制取决于实际采集方式，系统保护请求成功不等同于隐身成功，不能保证所有会议软件隐藏。发布前应在目标平台和实际接收画面复验。
