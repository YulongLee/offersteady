## ADDED Requirements

### Requirement: Use a legible companion icon at small sizes
桌面伴随程序 MUST 使用适合 Dock、任务栏和启动器小尺寸展示的图标。图标 MUST 具有透明外部圆角，MUST 保留产品核心盾牌、麦克风和确认标记，并 MUST NOT 包含缩小后不可读的产品名或说明文字。

#### Scenario: Operating system renders the 32 pixel icon
- **WHEN** macOS 或 Windows 将伴随程序图标缩小到约 32 像素
- **THEN** 图标仍能辨认核心图形且不会呈现为带白色方形画布的文字缩略图

### Requirement: Ship the icon in every supported installer
正式桌面发布 MUST 在 macOS arm64、macOS x64 和 Windows x64 安装包中包含相同品牌图标，并 MUST 使用高于上一正式版的版本号更新网页下载清单。

#### Scenario: User downloads a supported desktop package
- **WHEN** 用户从下载中心选择任一受支持平台
- **THEN** 下载到的新版本安装包包含更新图标且发布元数据的文件名、版本、大小和 SHA-256 与产物一致
