# Design QA: 首页典型使用反馈

## Evidence

- Source visual truth: 用户在本次对话中提供的“成功案例”两列六卡参考图（1105 × 682），仅采用其案例信息层级；人物头像、姓名、五星评分和雇主信息因真实性约束明确不复刻。
- Existing-page baseline: `/tmp/offersteady-commercial-audit/03-desktop-scenarios.png`（1240 × 1008）。
- Implementation desktop: `/tmp/offersteady-scenario-stories-qa/desktop-section.png`（1240 × 1338），CSS viewport 1440 × 1000，deviceScaleFactor 1。
- Implementation mobile: `/tmp/offersteady-scenario-stories-qa/mobile-section-320.png`（292 × 2395），CSS viewport 320 × 800，deviceScaleFactor 1；292px 为 `.public-shell` 扣除页面外边距后的实际区块宽度。
- Combined comparison: `/tmp/offersteady-scenario-stories-qa/desktop-before-after.png`（1320 × 760）。
- State: 未登录公开首页，深色主题。
- Browser verification: Playwright Chromium；确认六张卡片可见、320px 无横向溢出、浏览器控制台无 error。该区块没有交互控件，因此没有额外交互状态需要测试。

## Findings

没有遗留 P0、P1 或 P2 问题。

- Fonts and typography: 保留现有 Inter/系统中文字体栈；标题、岗位、典型困扰、正文和能力标签形成五级层次。正文桌面与移动端均为 12px、1.85 行高，无截断。
- Spacing and layout rhythm: 桌面两列三行，卡片内身份、困扰、叙述和能力标签间距一致；移动端按文档顺序单列排列，320px 无横向溢出。
- Colors and visual tokens: 继续使用现有背景、边框、文字和品牌绿色变量；真实性标识与重点区域使用品牌绿色，但不模拟五星评价。
- Image quality and asset fidelity: 参考图的人物头像被有意排除，使用项目已有 Phosphor 岗位图标，未引入占位头像、自制 SVG 或低清资源。
- Copy and content: 六个故事均标注“情景示例”；区块明确说明“非真实用户评价”，不包含真实姓名、具体雇主、评分、Offer 或效果数字。
- Accessibility: 图标标记为装饰内容；语义标题和正文顺序正确；辅助标签不承担唯一信息表达；页面保持 320px 可读。

## Comparison History

### Pass 1

- [P2] 320px 小屏正文被移动端样式降为 11px，案例信息较多时可读性偏弱。
- Fix: 删除移动端 11px 覆盖，使正文沿用 12px 基础字号。

### Pass 2

- 重新捕获桌面和 320px 小屏页面。
- 正文可读性改善，六张卡片无文字截断、重叠或横向溢出；没有遗留 P0/P1/P2。

## Implementation Checklist

- [x] 桌面两列六卡
- [x] 小屏单列六卡
- [x] 区块级与卡片级真实性说明
- [x] 岗位、面试类型、典型困扰、叙述和能力标签
- [x] 无伪造人物、头像、评分、雇主或录用结果
- [x] 320px 无横向溢出
- [x] 控制台无 error

## Follow-up Polish

- P3：获得真实且授权的用户反馈后，可将单张情景卡替换为可核验案例，并保留脱敏与授权说明。

final result: passed
