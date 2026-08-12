# Design QA: 手机端实时回答滚动

## Evidence

- Source visual truth: 用户在本次对话中提供的 iPhone 浏览器截图（945 × 2048），状态为实时面试已有长回答；截图显示悬浮操作栏遮挡正文，且答案无法继续上滑。
- Implementation full-view: `/tmp/offersteady-mobile-answer-qa/mobile-top.png`（390 × 844）。
- Implementation focused region: `/tmp/offersteady-mobile-answer-qa/answer-end.png`（318 × 81），为长回答最后一段。
- Viewport: 390 × 844 CSS px，deviceScaleFactor 1，Playwright Chromium，启用 mobile/touch。
- State: 合成长回答、两条实时对话、快答与截屏回答操作；不含真实用户数据。
- Density normalization: 实现按 CSS 1:1 捕获；源图包含手机浏览器界面，因此只比较产品内容中的滚动、遮挡和阅读区域，不比较浏览器外壳。

## Findings

没有遗留 P0、P1 或 P2 问题。

- Fonts and typography: 延续现有回答字号变量、中文字体栈与行高；长回答没有截断或被按钮覆盖。
- Spacing and layout rhythm: 手机端使用一个主纵向滚动区；对话、操作按钮和回答按页面流排列，回答卡片不再形成第二个固定高度滚动区。
- Colors and visual tokens: 没有改变现有深色主题、品牌色、边框或状态色。
- Image quality and asset fidelity: 本次界面无新增图片或图标资产。
- Copy and content: 保留快答、截屏回答、简单回答、详细回答和历史答案文案，没有改变业务含义。
- Interaction: 主滚动区 `clientHeight=746`、`scrollHeight=1525`，实际滚动至 `scrollTop=779` 后答案末段完整可见；操作栏和末段重叠为 0。
- Responsiveness: 390px 视口的页面 `scrollWidth=390`，无横向溢出；回答区 `overflow: visible`，操作栏 `position: static`。
- Accessibility: 触摸滚动使用 `touch-action: pan-y` 与 iOS 惯性滚动，原有按钮语义不变。

## Comparison History

### Pass 1

- [P0] 源截图中的回答被悬浮快答/截屏栏覆盖，嵌套固定高度滚动区在 iPhone 浏览器中抢占触摸手势，无法到达答案末尾。
- Fix: 移除手机端回答卡片的独立滚动和固定最小高度；取消操作栏 sticky；使主工作区成为唯一纵向触摸滚动容器。

### Pass 2

- 390 × 844 触摸视口实际滚动到最后一段；末段完整可见、无操作栏重叠、无横向溢出、控制台无错误。
- 没有遗留 P0、P1 或 P2。

## Implementation Checklist

- [x] 单一手机端纵向滚动区
- [x] 完整答案可滚动到末尾
- [x] 快答/截屏回答不遮挡正文
- [x] iOS 惯性触摸滚动
- [x] 无横向溢出
- [x] 保持桌面端布局规则不变

## Follow-up Polish

- P3：后续可根据真实用户习惯决定是否把对话区域默认折叠，让手机首屏更快进入回答。

final result: passed
