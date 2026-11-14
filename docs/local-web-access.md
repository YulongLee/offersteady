# 本地网页原型访问说明

状态：Active

当你感觉“本地网页原型访问不了”时，先不要默认判断为页面代码损坏。当前项目存在两条本地访问链路：

## 推荐访问方式

### 1. 开发态访问

```bash
npm run dev:web
```

默认访问：

```text
http://127.0.0.1:5173/
```

适合日常改页面、看即时更新。

### 2. 预览态访问

```bash
npm run preview:web
```

默认访问：

```text
http://127.0.0.1:4173/
```

适合执行自动巡检、回归验证和模拟更接近产物的访问方式。

## 快速诊断

先运行：

```bash
npm run doctor:web
```

它会检查：

- `http://127.0.0.1:4173`
- `http://127.0.0.1:5173`

并告诉你当前本地网页到底是：

- 服务未启动
- dev 服务可访问
- preview 服务可访问
- 访问地址不对

## 自动巡检前提

运行：

```bash
npm run review:live -w @offersteady/web
```

之前，必须至少有一个本地网页地址可访问。现在脚本会自动优先探测：

1. `OFFERSTEADY_REVIEW_URL` 指定地址
2. `http://127.0.0.1:4173`
3. `http://127.0.0.1:5173`

如果三个地址都不可达，脚本会直接报“本地网页不可访问”，而不是把问题误判成页面布局回归。

## 建议排查顺序

1. `npm run doctor:web`
2. 如果都不可访问，运行 `npm run dev:web`
3. 若需要巡检或稳定端口，再运行 `npm run preview:web`
4. 页面能打开后，再执行 `npm run review:live -w @offersteady/web`

## 手机面试滚动回归

```bash
npm run review:mobile-scroll -w @offersteady/web
```

此检查自行启动隔离的本地服务，使用实际回答、对话和模拟面试组件及合成数据，不需要已有登录态。外部网络请求会被阻断，不创建真实会话。检查 320×568、390×844、430×932、667×375 四种视口，覆盖长回答、长对话、模拟面试准备、作答及报告末尾操作。

运行环境需已有 Playwright 和浏览器。若它们位于工作区外，可通过 `PLAYWRIGHT_MODULE` 指定模块绝对路径，通过 `BROWSER_PATH` 指定浏览器路径，脚本不安装或下载组件。默认 Chromium 验证触摸滑动、回看位置和跟随最新转写。`BROWSER_ENGINE=webkit` 仅验证布局、滚动范围及滚动事件，因为当前驱动不支持移动 WebKit 的手势注入，不能视为 iPhone 真机触摸验收。

结果和截图默认保存在 `artifacts/mobile-scroll-review/`，可用 `OFFERSTEADY_REVIEW_ARTIFACTS` 指定其他目录。本检查不会发布网页。
