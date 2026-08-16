## Why

移除常驻屏幕预览后，桌面伴随程序仍沿用旧的固定窗口高度，导致连接管理下方出现大面积无意义留白。默认窗口应贴合当前核心控件，同时在内容增多或屏幕较小时保持可滚动。

## What Changes

- 缩小伴随程序默认窗口高度和允许的最小高度，使底部只保留正常安全边距。
- 保持现有宽度、控件密度、预览弹层和纵向滚动能力。
- 不改变音频采集、屏幕捕捉、连接管理或后台运行行为。

## Capabilities

### New Capabilities
- `compact-desktop-companion-window`: 定义桌面伴随程序紧凑默认窗口及内容溢出行为。

### Modified Capabilities

## Impact

- 影响 `apps/desktop` Electron 主窗口尺寸配置和回归测试。
- 不涉及服务端 API、用户数据或截图内容处理。
