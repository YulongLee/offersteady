## Why

国服当前 1.3.2 Apple Silicon 伴随程序将最低系统版本设置为 macOS 14.2，导致 Apple M2 但仍使用 macOS Ventura 13.4 的用户无法启动。需要生成一份不进入线上发布清单的专用兼容包，供该用户单独验证。

## What Changes

- 为 macOS 原生采集运行时和桌面应用打包增加可显式指定最低 macOS 版本的能力，默认行为仍保持 14.2 不变。
- 新增独立的 macOS arm64 Ventura 13.4 兼容构建命令，保持应用版本号为 1.3.2。
- 将兼容包、校验元数据和临时构建产物放在独立的 `apps/desktop/release/macos-compat-13.4-arm64/` 目录。
- 兼容包不写入线上发布清单、不上传 OSS、不改变现有线上 1.3.2 包。

## Capabilities

### New Capabilities

- `macos-ventura-compat-packaging`: 定义专用 macOS Ventura 13.4 arm64 构建、验证和隔离分发边界。

### Modified Capabilities

无。

## Impact

- 影响 `apps/desktop` 的本地构建脚本和 OpenSpec 变更文档。
- 不改变 Web、后端、实时协议、计费、权限逻辑或正式线上下载清单。
- 兼容包仍需在真实 macOS Ventura 13.4 设备上验收麦克风、系统音频、屏幕权限和设备连接；当前构建机为 macOS 15，无法替代该实机验收。
