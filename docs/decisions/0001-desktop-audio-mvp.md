# ADR 0001：桌面音频 MVP 平台与技术路线

状态：Superseded by ADR 0002  
日期：2026-06-29

## 决策

1. 首发平台为 Windows 11，原型最低支持 Windows 11 24H2；正式发布时最低版本必须仍处于微软支持周期。
2. 麦克风与系统音频使用独立来源和序列，平台不支持时才退化为混合输入或单一来源。
3. MVP 桌面壳采用 Electron，界面使用与 Web 相同的 React/TypeScript 基础；平台采集能力位于可替换适配器中。
4. macOS 作为第二平台，等 Windows 闭环和真实用户验证完成后实现。

## 依据

- StatCounter 2026 年 5 月中国桌面访问数据中，Windows 占约 78.9%，明显高于 Apple 桌面系统：https://gs.statcounter.com/os-market-share/desktop/China
- 微软文档说明 WASAPI loopback 可以采集系统音频混音，且不依赖硬件提供 loopback 设备：https://learn.microsoft.com/windows/win32/coreaudio/loopback-recording
- Electron 官方 `desktopCapturer` 支持通过 `audio: "loopback"` 请求桌面音频：https://www.electronjs.org/docs/latest/api/desktop-capturer
- Windows 11 24H2 Home/Pro 支持截至 2026-10-13，因此它只作为当前原型下限；正式发布前需要重新核对生命周期：https://learn.microsoft.com/lifecycle/products/windows-11-home-and-pro

## 取舍

Electron 的安装体积和内存开销高于原生程序或 Tauri，但它可以复用 TypeScript、React 和 Chromium 音频能力，更适合快速验证产品闭环。如果 Electron 的系统音频稳定性无法达到要求，保留协议和 UI，替换底层为 Windows 原生 WASAPI 采集适配器。

## 验证边界

当前开发环境是 macOS，能够验证协议、Web、桌面状态机和麦克风通用接口，但不能证明 Windows loopback 的真实行为。Windows 11 虚拟机或实体设备测试是系统音频任务的完成条件。
