# Tests

- `integration/`：跨模块或跨服务的集成测试。
- `e2e/`：从用户入口验证完整流程的端到端测试。

单元测试应靠近被测代码。

实时面试页的浏览器布局与无障碍树检查：

```bash
npm run build --workspace @offersteady/web
npm exec --workspace @offersteady/web -- vite preview --host 127.0.0.1 --port 4173
# 在另一个终端执行
npm run review:live --workspace @offersteady/web
```

检查覆盖手机、平板、桌面、200% 等效缩放、窄屏横向、长文本、44px 触控目标、资料抽屉、缩小可视高度和 Chromium accessibility tree。截图与 JSON 报告默认写入系统临时目录 `offersteady-live-review/`；可用 `OFFERSTEADY_REVIEW_ARTIFACTS` 修改位置，用 `CHROME_PATH` 指定 Chrome/Chromium。
