# 国服模拟面试启动权限提示排查：2026-10-29

本次是用户反馈后的只读检查，未开发或部署修复，未修改真实用户/权限/配置，未调用真实麦克风、模型、音频播放或收费面试。反馈者的系统、提示位置和完整文案尚未提供，因此不能把全部反馈归于同一原因。

## 已确认的权限状态误判

### 正式版的未知状态会被提示为未开启麦克风

当前实际Backend的 `_device_readiness` 对 `mockInterviewProtocol=1` 要求 `microphone=granted`；`unknown`、缺失和显式拒绝都返回同一 `mock_microphone_required` / “请在助手中开启麦克风权限。”。旧v2且无专用mock标识的unknown才使用历史deferred兼容。

“未知”本身不能说明OS已拒绝。初次登记使用renderer初始unknown，后台授权及主进程周期登记可能尚未完成；在这段状态不同步窗口，准备页可以显示上述提示。相关现有15项合成准备检查通过，其中明确复现专用mock协议unknown被拦截，不是推测HTTP错误文案。

Windows数据流已进一步用实际启动回调、实际IPC handler和实际DesktopCapabilitySnapshot合成复现：启动的唯一renderer注册先发unknown；后台IPC返回true后本地状态改granted，但没有立即发新的能力登记。主进程快照仍是unknown，多次心跳也继续unknown。绑定后device-status成功上报并被主进程remember，下一轮15秒心跳才可持久化granted。因此本地显示granted与后端已收到granted之间确实存在窗口，不能称为永久无法恢复。Windows该IPC本身直接返回true，没有实际OS/媒体检查，故本地granted也不证明真实采集可用。

线上只读设备能力汇总中，近24小时登记的Windows 1.3.5 / mock协议1有12台microphone=unknown，其中检查时5台在45秒在线窗口内。这里只证明此元数据状态实际存在，**没有验证这些设备的OS真实授权，也没有按用户身份认定投诉者命中**。不输出设备ID、机器码、账号或音频。

### Mac后台授权超过2.5秒会丢弃晚批准

正式1.3.5的 `requestMicrophoneAccessInBackground` 使用 `Promise.race`，2.5秒超时直接返回false。启动回调把false映射为renderer权限denied；用户之后点允许也不再处理其结果。AST抽取正式实际函数，使用合成计时器和授权Promise，已复现超时后再批准仍保留denied，两种晚批准顺序均成立。快速批准对照为granted。

这属于助手状态误判，不能称OS每场都会重新请求授权。Mac主进程每15秒登记会读取真实OS授权，并以OS状态覆盖陈旧renderer快照，从而可修正后端能力；`device-status`只保存事件，不直接重写设备登记权限。没有“后端永久被denied反复覆盖”的证据。

## 模式提示和播放许可需要区分

- 模拟面试正式采集只使用麦克风；后端准备检查不要求屏幕录制权限。
- 助手在识别到mock绑定前仍启动普通双通道预检测，界面仍显示电脑输出/屏幕行；可能出现与模拟面试无关的权限提醒。Mac屏幕许可函数仅立即读取OS状态，**没有证据说它长期等待弹窗而阻塞麦克风上报**。
- 当前实际网页不调用getUserMedia，不申请麦克风或录屏。开始按钮在点击回调里立即执行AudioContext.resume后发送start，没有发现首次开始普遍丢失用户手势。
- 网页的“请点击朗读以允许浏览器播放声音。”来自播放器AudioContext非running检查。之前已解锁后被系统挂起也会出现同文案，不等于系统麦克风权限失效。
- 刷新/重连恢复speaking时，自动resume来自WebSocket回调；在不允许自动启动的浏览器条件下可以等待，当前缺少明确的点击恢复提示。已有sticky activation时不一定命中，不能称所有重连必失败。合成场景还复现自动/手动resume先后完成可能各发送speak的次生风险，未认定用户实际发生。

## 来源与验证

当前Backend为 `sha256:3e56917daba635e780d9bd728694d823494b40a6ab67a9968c5371c1378abb3e`，Web为 `sha256:99822e10e7b516aefe4ad96248f9eea631d90b057cb77b8dd386cff4830516fb`。只读逐SHA核对mock runtime、mock路由、realtime service和下载清单与本地一致；三平台公开助手仍为1.3.5。相关6份桌面源码与正式助手标签 `release-cn-companion-1.3.5-20261015`逐字一致。相关新性能发布没有改动这些权限逻辑。

实际Web来源353份公开文件清单，实际模块`main-559fbe0b.js`与`MockInterviewPage-411e4a78.js`逐SHA核对；从实际JS提取播放器验证6个合成场景；实际桌面函数验证6个合成场景。相关既有Web22项、Desktop23项、Backend准备检查15项通过。这些结果确认既有保护及复现边界，不能代替投诉者设备或真实OS权限验收。

脱敏证据在 `artifacts/cn-mock-permission-20261029/`：`production-scope.json`、`backend-permission-state-summary.json`、`backend-readiness.junit.xml`、`desktop-permission-repro.json`、`desktop-existing-tests.txt`、`web-bundle-permission-verification.json`。只保存源码/公开字节指纹、计数和合成状态，没有原始用户日志、音频、简历或凭据。

相关代码：[后台授权](../../apps/desktop/src/renderer/CompanionApp.tsx#L290)、[独立模拟麦克风](../../apps/desktop/src/renderer/audio/mock-microphone.ts)、[设备准备校验](../../apps/backend/app/services/mock_interview_runtime.py#L83)、[网页播放](../../apps/web/src/mock-interview-client.ts)。相关历史：[1.3.5发布](../releases/companion-1.3.5-cn-20261015.md)、[Mac签名旧缺陷](cn-mock-latency-mac-20261015.md)。旧1.3.2签名缺陷已有正式修复，不能据旧记录认定当前1.3.5仍缺签名权限。

待修方向是把unknown/超时/拒绝分开，授权结果按生命周期接收并及时同步；按模拟模式只要求实际必要权限；播放恢复单独显示。不得通过伪造granted、绕过OS或放宽账号/机器码/绑定代际来掩盖问题。具体开发和发布另行按用户授权管理。
