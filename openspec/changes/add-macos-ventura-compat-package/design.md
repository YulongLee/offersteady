## Context

当前正式 macOS 构建配置和 native capture runtime 都以 macOS 14.2 为最低版本。用户反馈的机器为 Apple M2，但系统为 macOS Ventura 13.4；兼容问题来自系统版本而非 CPU 架构。

## Design

1. `build-native-runtime.mjs` 读取 `OFFERSTEADY_MACOS_MIN_VERSION`，未设置时仍使用 14.2；兼容构建传入 13.4.0，让 Swift runtime 的 deployment target 与应用保持一致。
2. 新增 `package-ventura-compat-mac.mjs`，基于现有 release builder 配置生成临时配置，仅覆盖输出目录、最低系统版本和未公证的专用构建标识；正式 release 配置文件不被修改。
3. 兼容构建保留应用版本号 1.3.2，但产物文件名带 `Ventura13.4`，并在独立目录生成 DMG、校验值和元数据。
4. 兼容包使用已有 Developer ID 签名，但本任务不提交 Apple 公证、不上传 OSS，也不生成线上可下载条目。未公证状态必须在交付说明中明确。
5. 通过 `plutil`、`codesign`、`hdiutil` 和归档内容检查验证最低系统版本、目标架构、应用签名和产物隔离；真实 Ventura 13.4 采集能力列为待实机验收。

## Non-Goals

- 不修改正式 1.3.2 的最低系统要求。
- 不为 macOS 13.4 提供新的业务功能或降级实时协议。
- 不修改线上服务、后端清单或用户下载页。
