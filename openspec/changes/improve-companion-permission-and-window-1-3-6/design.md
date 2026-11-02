## Context

状态：用户已授权实现，本地-only。封版已推送且远端标签/分支均指向00d79ce；当前开发分支codex/companion-1-3-6-local。现有Electron42.5.0与正式国服身份、mock协议1/主协议2保留。需求与确证问题见proposal及docs/diagnostics/cn-mock-permission-20261029.md。

## Goals / Non-Goals

目标：真实权限、及时同步、麦克风故障可恢复；用户主动隐藏与透明图标点击唤回；本地1.3.6安装包可连接现有国服。

非目标：生产/OSS/Global发布、网页/Backend、协议/计费/模型/依赖升级、系统提示规避、投屏绝对不可见、真实音频上传或自动开始真实面试。

## Decisions

1. 主进程增加结构化麦克风snapshot读取和单次request IPC（permission/pending/source），保留旧boolean API兼容但Win不再无条件true。renderer不将2.5秒等待变成拒绝，保留真实异步结果及生命周期隔离；显式检查的媒体探测立即停止，不上传。OS授权与设备可读性分别判断。
2. 权限变化后同步ref/UI/现有register，单次在途+合并变化；失败保留待同步并由既有周期重试，无新持续轮询。保持主进程15秒登记。mock仅检查/呈现麦克风，普通/笔试策略不回退。
3. MockMicrophone保持现有回调与服务器epoch。resume最多3秒且必须running；仅当前context/track的真实ended或持续mute触发失败，短暂mute允许恢复。失效时先隔离PCM和回调，再幂等释放，保留题目及显式重试，不自动重开或复活暂停；AudioContext失败不冒充OS拒绝。
4. 主进程统一窗口可见状态，隐藏只改变自有UI：原窗口hide、Win任务栏跳过、Mac Dock hide；同一Tray仅切换为非空固定尺寸alpha=0图像，保留可点击槽位及事件。左击隐藏槽位恢复同窗口及正常图像；Win右键菜单保留，Mac隐藏时解除自动左键菜单绑定避免点击同时弹菜单，右键通过menu.popup显式使用隐藏mainWindow宿主提供原菜单（不传屏幕坐标，不经过Tray合成左击路径）。恢复不得依赖图标重建成功。再次点击应用通过既有single-instance/activate恢复；新增Cmd/Ctrl+Shift+H备用快捷键，冲突时仍保留应用唤回。所有ready-to-show/崩溃恢复遵守隐藏状态；进程重启默认可见。Mac Dock快速hide/show串行协调且迟到操作受意图代际约束，避免旧hide覆盖新restore。
5. 隐藏状态不改采集、绑定、心跳或截屏；不销毁renderer。网页现有状态/停止继续有效，OS指示器不处理。本需求明确替代历史变更的桌面持续入口呈现，非静默录音模式，不持久化自动隐藏。
6. 版本package/锁1.3.6。使用签名prepare-only构建国服Mac本地App（旧local packager引用缺失entitlements，不使用），保留相同bundle/team身份和实际主/Helper音频输入权限；封ZIP/本地DMG，不公证上传。Win用既有packager，核验PE/内外归档及冻结dist。两Mac架构顺序构建，保持同一源manifest；产物无local-test-runtime/global配置，默认HTTPS国服，无服务器凭据。

## Risks / Trade-offs

- [透明槽位难发现] → 原槽位保持可点击，左击直接恢复；应用图标重新打开同一实例+快捷键备用，窗口缺失时显式重建，进程重启可见。
- [隐藏影响音频/恢复误弹] → 保留backgroundThrottling:false，窗口与capture状态分开；合成生命周期和本地隔离壳验证，硬件验收单列。
- [OS/蓝牙差异] → 区分代码回归和实体机器，拒绝将结构验证称真实音频通过。
- [本地签名缺公证] → 实际签名/entitlement验证，明确本地包未公证，不禁用Gatekeeper或重置系统授权。

## Migration Plan

本次无生产迁移。先本地回归、类型、构建和签名/架构/地址/字节核对，再提供安装包；用户完全退出旧助手后自行安装测试线上。旧正式1.3.5及Git封版保持，可退出本地测试版后重新安装旧版。

## Open Questions

无阻塞需求问题。实体Windows/Intel Mac音频需对应设备验收；本机自动测试不登录真实账号、不启动收费面试。

## 首轮验收修订

移除新增独立麦克风检查按钮、独立提示块及其展示状态，恢复原行布局；已有错误态“重试麦克风”仍复用内部权限协调器。隐藏按钮样式保持。透明图像需至少16×16逻辑尺寸且像素全透明，不使用createEmpty/null；Tray实例、位置、事件在隐藏时保持。原生Mac验证非空全透明图像、实际Tray不变且正尺寸边界不变、点击处理恢复及隐藏宿主原生菜单；另尝试真实指针点击，不把程序化emit当实际点击。CUA因无对应窗口无法点击系统菜单栏时如实记录为待用户本机验收，不阻止提供本地包，不宣称物理点击通过。Windows/Intel硬件限制如实记录。相同1.3.6版本用Local-r2文件名区别首轮安装包，不改官方清单、不上传或部署。
