# Web 本地笔试失败反馈验证

2026-11-01，仅本地源码/合成输入。无 Backend、API、计费、模型、SEO、发布或线上登录改动。

## 已完成

- 既有失败弹窗/多屏提示区区分当前 Backend 的助手心跳过期、绑定失效、`capture-failed`、`upload-failed`。普通模式保持原错误文案。没有新增常驻提示、按钮或布局。
- `ScreenshotTask.failureStage` 仅前端可选元数据，透传已存在的服务端 stage；旧响应缺少该值仍可用，不改变请求或 JSON client。
- 单屏请求固定自己的 controller，已取消请求的迟到 stage、回答、失败和清理不能覆盖/清除新请求。快捷键取消确认使用 attempt epoch，覆盖“新请求已经完成，旧取消才返回错误”的情况。
- 多屏捕获失败保留已有图片，既有截屏/重新截屏入口可恢复，未自动重复提交或调用模型。

## 自动验证结果

```sh
npm run test -w @offersteady/web -- src/written-screenshot-feedback.test.ts src/backend-adapter.written-multi-screen.test.ts src/App.written-multi-screen.test.tsx
# 3 files / 46 tests passed
npm run test -w @offersteady/web -- src/App.focused-live.test.tsx src/App.states.test.tsx src/backend-adapter.test.ts src/backend-adapter-state-stream.test.ts
# 4 files / 102 tests passed
npm run typecheck -w @offersteady/web
# passed
```

覆盖：当前 Backend 绑定文案、捕获/上传 stage、无 stage 的旧响应、离线后的既有重试、多屏保留已有图片、旧取消迟到 409、旧结果 resolve/reject/stream 回调、新任务仍可取消、快捷键旧取消晚于新任务完成、普通模式文案不变。

## 无外部请求的本地构建

标准 Vite build 的 pricing 插件会读取线上 public state。本次不运行该读取；程序化加载现有配置，使用 development mode，仅过滤该插件，并显式禁止构建时 fetch。未改 pricing 源码或配置，构建产物不用于部署，也不等同完整生产发布构建。

从仓库根目录执行的完整方式：

```sh
node --input-type=module <<'JS'
import { build, loadConfigFromFile } from 'vite';
import { resolve } from 'node:path';
const webRoot = resolve('apps/web');
globalThis.fetch = async () => { throw new Error('Network is disabled for this local synthetic build'); };
const loaded = await loadConfigFromFile({ command: 'build', mode: 'development' }, resolve(webRoot, 'vite.config.ts'));
if (!loaded) throw new Error('Web config was not found');
const plugins = loaded.config.plugins.filter(plugin => plugin?.name !== 'cn-production-pricing-static');
if (plugins.length !== loaded.config.plugins.length - 1) throw new Error('Expected one production pricing sync plugin');
await build({ ...loaded.config, plugins, root: webRoot, configFile: false, mode: 'development', build: { ...loaded.config.build, outDir: '/tmp/offersteady-written-feedback-web-local', emptyOutDir: true } });
JS
```

结果：360 modules transformed，build passed。输出目录 `/tmp/offersteady-written-feedback-web-local`，未覆盖生产或仓库 dist。

## 本地交互预览

```sh
npm run dev -w @offersteady/web -- --host 127.0.0.1 --port 5184 --strictPort
```

测试入口：`http://127.0.0.1:5184/test-previews/written-multi-screen.html`。该入口不属于生产 Vite input，每个 adapter 操作均使用合成内存且 fetch 显式失败。URL 的 `scenario` 可选值：`assistant-offline`、`binding-invalid`、`capture-stage-error`、`upload-stage-error`、`cancel-late-error`；前四种仅模拟一次失败，原有入口再次截屏可成功。取消场景的首请求故意忽略 abort 并在 6 秒后报 409，用于验证旧回调隔离。

隐藏的独立本地浏览器页已检查离线失败、原按钮重试成功、上传失败、取消首请求后新请求成功且不被迟到 409 覆盖。证据保存在本地 `artifacts/written-web-feedback-local-20261101/`（合成画面）。没有访问用户现有线上标签页、真实账号、截图、模型或付费流程。

限制：这些是合成 UI/adapter 回归和本地开发构建，不证明真实网络/实体助手恢复，不证明完整生产构建或发布兼容；后续统一发布仍需按实际运行 Web 基线制作最小增量并验收。
