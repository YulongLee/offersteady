## Context

现有手机实时面试通过两层 grid 限制整页高度，内容通过页签切换。回答由外层 `.mobile-live-panel` 滚动。对话列表需要由内层 `.conversation-list` 滚动，因为 `ConversationMonitor` 在该节点检测用户是否回看，并自动跟随新转写。

## Decision

手机对话卡片使用面板可用高度，允许其 flex 子列表收缩。外层面板仍保留滚动兜底。对话内容超过面板时，列表产生真正的滚动范围，避免无范围的内层滚动容器阻断外层触摸手势。

不删除全局 `overscroll-behavior`，以免影响桌面对话回看和滚动边界。不把手机改为全页面堆叠，也不修改模拟面试已经正常的页面滚动。

## Verification

使用当前实际组件、合成长回答及多段转写构造隔离页面。浏览器注入触摸滑动，检查列表滚动位置和末段可达性，不能只通过设置 `scrollTop` 或 CSS 字符串判断。覆盖窄屏、常见手机、短视口，另检查模拟面试准备、作答及报告页面滚到底部。使用 Chromium 验证触摸，WebKit 验证布局与滚动范围。运行相关单元测试、网页类型检查及构建。

## Non-goals

不新增移动端收音能力，不调整面试业务交互，不发布到两服，不更改桌面助手。

## Verification results (2026-11-12)

- 修复前 Chromium 实际触摸探针：回答面板滑动 350px，对话文字上的相同手势滚动 0px。实际组件浏览器回归因对话列表滚动范围为 0 而失败。
- 修复后 Chromium 16 个场景通过，覆盖 320×568、390×844、430×932、667×375，每种视口包含实时面试、模拟面试准备、作答和报告。实际触摸滑动能够回看对话、到达长回答及模拟页面末尾。新增转写不打断手动回看，位于底部时继续跟随最新。
- WebKit 同样 16 个场景通过，仅验证布局、程序滚动及事件，不宣称已完成 Safari/iPhone 真机触摸验收。
- `npm run test -w @offersteady/web -- src/styles.appearance.test.ts src/App.focused-live.test.tsx src/MockInterviewPage.test.tsx`：3 个文件、86 项通过。
- `npm run typecheck -w @offersteady/web` 及包含浏览器夹具的额外类型检查通过。
- `VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=mobile-scroll-local-20261112 npm run build -w @offersteady/web` 通过，构建仅保存在本地。
- `openspec validate fix-mobile-interview-scroll --strict` 通过，`git diff --check` 通过。

脱敏测试输出及截图位于 `artifacts/mobile-interview-scroll-20261112/`。复现入口和环境参数见 `docs/local-web-access.md` 的“手机面试滚动回归”。当前尚不知道反馈者的手机型号、浏览器及具体页签，仍需由其实际设备复核。没有更改生产服务。
