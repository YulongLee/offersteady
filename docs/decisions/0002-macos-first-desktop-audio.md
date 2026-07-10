# ADR 0002：macOS 首发与 Universal 构建

状态：Accepted  
日期：2026-06-29  
取代：ADR 0001 的 Windows 首发决策

## 决策

1. 桌面伴随程序首发平台改为 macOS 14.2 或更新版本。
2. 同时支持 Intel x64 与 Apple Silicon arm64，发布一个 universal DMG，用户无需判断芯片类型。
3. 继续使用 Electron + React/TypeScript；Electron Builder 使用 `universal` 架构合并 x64 与 arm64 产物。
4. 麦克风与系统音频保持独立来源。系统音频首选 Electron `desktopCapturer` 当前使用的 CoreAudio Tap 路径。
5. Windows 调整为第二阶段平台。

## 依据

- 当前只有 Mac 测试设备，macOS 首发可以形成真实的本地开发、权限验证和音频验收闭环。
- Electron Builder 支持 `x64`、`arm64` 和同时包含两种架构的 `universal` macOS 构建：https://www.electron.build/docs/architecture/
- Electron 的桌面音频文档说明 macOS 14.2+ 需要 `NSAudioCaptureUsageDescription`，当前 Chromium/Electron 使用 CoreAudio Tap：https://www.electronjs.org/docs/latest/api/desktop-capturer
- Apple ScreenCaptureKit 原生支持采集屏幕音频，并提供系统权限与音频样本接口：https://developer.apple.com/documentation/screencapturekit

## 取舍

Universal 安装包体积接近单架构版本的两倍，但只有一个下载入口，对早期用户更简单。当前工程没有原生 Node 模块，因此 universal ASAR 合并风险较低；未来引入原生模块时，必须同时验证 x64 与 arm64 构建。

## 验证要求

- 当前 Apple Silicon Mac 验证 arm64 运行、麦克风权限和系统音频权限。
- CI 或 Intel 测试机验证 x64 构建；至少使用 `lipo -info` 检查发布包同时包含 `x86_64` 与 `arm64`。
- 正式外部分发前完成 Developer ID 签名与 Apple notarization。
