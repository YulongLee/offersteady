## ADDED Requirements

### Requirement: Companion opens with a compact default height
桌面伴随程序 SHALL 使用贴合当前主页面核心内容的默认窗口高度，不得在连接管理和页脚下方保留大面积无功能留白。

#### Scenario: Companion opens in its default state
- **WHEN** 用户打开伴随程序且没有额外展开弹层
- **THEN** 默认窗口完整展示品牌栏、音频控制、屏幕控制、连接管理和页脚
- **AND** 页脚下方仅保留正常安全边距

### Requirement: Compact window preserves access to overflowing content
桌面伴随程序 MUST 在窗口缩小或状态内容增长时保留纵向滚动能力，不得裁切不可恢复的核心操作。

#### Scenario: Content exceeds the available window height
- **WHEN** 状态提示、系统缩放或用户调整窗口导致内容高度超过视口
- **THEN** 用户可以纵向滚动访问连接管理和页脚内容
