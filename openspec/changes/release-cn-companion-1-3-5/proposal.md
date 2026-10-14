## Why

用户已在 2026-10-15 明确要求将本轮助手版本部署上线，Windows 和 macOS 都升级。本轮发布已经本地验证的麦克风签名、采集状态、失败提示和能力登记修复，提供正式下载。

## What Changes

- 国服助手统一发布版本 1.3.5：macOS Apple Silicon、macOS Intel、Windows x64。
- Mac DMG 必须通过 Developer ID 签名、公证与 stapler/Gatekeeper 检查，并包含实际音频输入签名权限。
- Windows NSIS 安装包验证 x64 可执行文件、安装器载荷与编译内容，保留真实未签名状态。
- 所有安装包先上传不可变 OSS 版本路径；三个平台全部准备成功后原子更新国服下载清单，保留回滚材料。
- 以实际线上清单与组件为基线更新发布元数据，优先热更新清单避免中断当前面试。

## Capabilities

### New Capabilities

- `cn-companion-1-3-5-publication`: 同版本三平台客户端构建、验证、下载清单与回滚。

### Modified Capabilities

无。使用现有助手身份、协议、国服地址和下载 API。

## Impact

Desktop 版本及编译产物、OSS 版本对象、国服发布清单和交付记录。当前正式 Mac 最低系统 14.2+、Windows 10 22H2+ 保持；私有 Ventura 兼容包不改动。不自动发布 Global、不部署本地后端出题优化、不变更计费或处理真实用户问答。
