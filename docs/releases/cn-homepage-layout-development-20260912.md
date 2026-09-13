# 国服首页排版优化：本地开发与验收

日期：2026-09-12（北京时间）

状态：本地候选版本完成，未部署。候选标识 `cn-homepage-layout-20260912.local` 不是生产版本号。

## 来源与边界

先检查实际生产页面及源码。主工作区的国服首页落后于生产，不可直接作为发布基线；本轮没有把旧页面覆盖到线上，也没有将生产 App 覆盖到主工作区。此前对旧页面的本轮修改已撤回，用户原有工作区改动保留。

只读取得生产 Web 所用源码 `/opt/offersteady/releases/20260911-cn-alipay-review-login-1`。生产 `current` 指向 `/opt/offersteady/releases/20260911-disable-wechat-compatible-1`，两者的 App.tsx 和首页商业样式文件校验值一致。副本不包含服务器环境变量或真实用户数据。

实现目录：`artifacts/cn-homepage-layout.82qdGV/candidate/`。未修改基线目录：`artifacts/cn-homepage-layout.82qdGV/baseline-check/`。这两个目录被 Git 忽略，因此另行交付持久化的 [精确源码补丁](../../design/previews/cn-homepage-layout/source.patch)。补丁已对未修改基线执行 `git apply --check`，四个目标文件全部检查通过；不要直接应用到旧主工作区。

本轮没有生产写入、部署、服务重启、订单创建或支付操作，没有修改海外版。

### 基线文件 SHA-256

| 文件 | SHA-256 |
| --- | --- |
| apps/web/src/App.tsx | c0c692a4a711ebf239c045bb1318ffbc41e7d70bff27e4cb4e34810b480ba54d |
| apps/web/src/homepage-commercial.css | 68cd5ff47e54821bd603fce4c0a6462b30eb675980d31b8403cb48cb9abad2cc |
| apps/web/index.html | 051dbed2be583ed5394d551422ea5cbbc2e54b19d2c89475ce7abdf5acb13dda |

## 修改内容

| 文件 | 原因与修改 |
| --- | --- |
| apps/web/src/homepage-commercial.css | Windows/macOS 按钮等宽对齐；缩减首屏多余留白；移动导航适配；窄屏卖点卡改为图标与正文并排；修复两个卡片背景引用未定义变量的问题；套餐权益链接保持至少 44px 点击高度。 |
| apps/web/src/App.tsx | 仅首页添加 `cn-home-shell` 样式作用域；首页套餐查看链接改为公开 `/pricing`。其他页面不启用新增导航样式。 |
| apps/web/index.html | 同步初始 HTML 中公开价格链接及说明。Title、H1、Canonical 及核心 SEO 内容保留。 |
| apps/web/src/homepage-layout.test.tsx | 新增 8 项回归测试，覆盖首页作用域、现有入口、真实 manifest 下载行为、Mac 菜单、价格来源及静态 HTML。 |

原有 HomepageDownloads 组件、Windows 下载地址解析、Mac 架构选择、Escape 关闭与焦点恢复均未改动。不新增下载描述或重复下载入口。

套餐金额、计费费率、后端接口、登录、支付及面试业务逻辑均未修改。匿名用户可以先查看公开价格；购买仍由原账户内账单流程完成。

OpenSpec 限定了展示层改动范围；page-cro 检查用于保留既有主要行动，集中现有下载入口并改善公开价格可达性，没有加入未经验证的营销数字。

## 验证结果

最终验证使用各自生产副本中的 `@offersteady/config` 和 `@offersteady/protocol`，避免共享 node_modules 解析到主工作区旧协议。未改动共享依赖或锁文件。

| 检查 | 结果 |
| --- | --- |
| Web typecheck | 通过 |
| Web production build | 通过 |
| verify-pricing-live.mjs | 通过：构建与当时生产目录 10 个商品一致，快照小于 24 小时 |
| 新增首页测试 | 8/8 通过 |
| 未修改生产副本全量测试 | 363/373 通过，10 项失败 |
| 优化候选全量测试 | 371/381 通过，10 项失败 |
| 基线与候选失败集合比较 | 完全一致，新增失败 0 |
| 源码补丁基线检查 | 通过，未实际应用到基线 |

全量测试不能宣称全部通过。既有失败分布：

- `App.product-experience.test.tsx`：6 项，旧首页标题、六功能、平台展开和产品指标等预期与生产页面不一致。
- `App.test.tsx`：1 项，旧首页标题断言。
- `App.partner-program.test.tsx`：2 项，合作入口显示条件的旧预期与生产源码不一致。
- `App.material-actions.test.tsx`：1 项，删除失败后的网络错误文案断言。

未借本次版式优化修改这些测试预期或改变对应业务。详细本地测试证据：`artifacts/cn-homepage-layout.82qdGV/baseline-tests-isolated.json` 和 `candidate-tests-isolated.json`。

执行命令（在候选 `apps/web/`）：

```sh
npm run typecheck
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-homepage-layout-20260912.local npm run build
node scripts/verify-pricing-live.mjs
npm test -- --reporter=default --reporter=json --outputFile=../../../candidate-tests-isolated.json
```

最终产物主 JS 444.35 kB（gzip 133.43 kB），CSS 119.19 kB（gzip 21.72 kB）。没有修改体积阈值或重构业务 Bundle；这些数值不是线上加载速度或转化率改善的证明。

## 视觉与交互检查

本地浏览器实际检查 320、390、900、1440px 四种宽度，均无页面横向溢出。下载按钮均等宽且高度 48px，套餐权益入口高度至少 44px。320px 下 Mac 菜单完全在视口内，Escape 关闭且焦点回到菜单按钮；未触发真实安装包下载。

- [桌面 1440px](../../design/previews/cn-homepage-layout/hero-1440.png)
- [中屏 900px](../../design/previews/cn-homepage-layout/hero-900.png)
- [手机 390px](../../design/previews/cn-homepage-layout/hero-390.png)
- [窄屏 320px](../../design/previews/cn-homepage-layout/hero-320.png)

预览：[本地首页候选](http://127.0.0.1:5187/layout-preview.html)。该入口使用明确标注的合成套餐/下载数据，只用于版式检查，不是生产计费界面；未调用真实支付或面试链路。预览 HTML 和 fixture 没有加入生产构建入口。

## 后续发布注意

本次未上线，线上网站保持原样。用户验收后若要发布，应重新核对生产基线、只应用本次补丁并重跑构建与生产价格校验，避免覆盖后续线上改动或携带其他未确认工作区改动。
