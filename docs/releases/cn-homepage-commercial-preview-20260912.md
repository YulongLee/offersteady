# 国服首页商业化排版本地预览

版本：`cn-homepage-commercial-20260912.local`。仅本地预览，未部署国服或国际服。

预览地址：<http://127.0.0.1:5187/>。支持刷新；本地服务需要保持运行。

## 范围与实现

按用户要求保留现有深色/绿色品牌、首页定位和 Windows/macOS 下载入口。本次使用 OpenSpec 管理已确认范围，并按页面转化审查方法，将产品证据、使用方法和购买说明放在更容易理解的位置。

主工作区 Web 源码落后于线上，因此在 `artifacts/cn-homepage-layout.82qdGV/candidate` 的隔离生产副本实施，没有用整份生产文件覆盖主工作区已有修改。生产基线来源和第一轮记录见 [前一轮报告](cn-homepage-layout-development-20260912.md)。

1. 首屏采用不对称布局，保留原 H1，突出真实产品界面。
2. 新增“项目追问 / 截图问题”展示切换及大图查看，明确标注合成示例。
3. 将原有操作视频前移至套餐之前；视频不自动播放，预加载设为 none；产品概览视频默认折叠。
4. 功能区减少重复卡片，改用分栏、分隔线和更清晰的留白。
5. 套餐区解释积分与会员的区别、有效期、截图/回答权益、知识库限制及交付；复用既有配置，不改变计费逻辑。
6. 静态初始 HTML 同步主要正文；公开价格入口保持 `/pricing`，未修改 canonical 策略。

## 文件

隔离副本中的运行时变更：

- `apps/web/src/App.tsx`：首页区块顺序、首屏和套餐文案展示。
- `apps/web/src/HomepageProductPreview.tsx`：演示场景切换组件。
- `apps/web/src/homepage-commercial.css`：限定国服首页的响应式样式。
- `apps/web/index.html`：初始 HTML 内容同步。
- `apps/web/public/media/homepage/project-demo.png`、`screenshot-demo.png`：直接复用项目现有视频素材中的真实界面合成示例，没有引入用户数据。
- `apps/web/src/homepage-layout.test.tsx`：12 项首页回归测试。

仅预览支持文件：`layout-preview.html`、`src/test/layout-preview.tsx`、`vite.layout-preview.config.ts`。这些文件隔离预览数据，映射公开静态页面，不进入正式发布补丁。顶部预览提示不属于正式页面。

## 验证结果

- `npm run typecheck`：通过。
- `npm run build`：通过，生产模式版本标识为上述 local 版本。
- `node scripts/verify-pricing-live.mjs`：通过，构建价格目录与当时生产 10 个商品一致。
- 首页回归：12/12 通过。
- Web 全量：385 项，375 通过、10 失败；未修改生产基线为 373 项、363 通过、同样 10 失败。按失败用例名称比较，无新增失败。既有失败涉及旧首页/入口断言及资料错误提示，未在本轮扩大修复范围。
- 构建主 JS：447.75 kB，gzip 134.42 kB；CSS：126.63 kB，gzip 22.92 kB。未放宽体积阈值，也未重构业务 Bundle。
- 浏览器实际检查 320、390、900、1440 px：无横向溢出，两个下载按钮可见；320 px 的 macOS 菜单未越界且 Escape 能关闭。
- 演示图切换、教程锚点、原有教程视频实际播放/暂停、公开价格页面跳转及返回：通过。
- 本次检查时浏览器错误日志为空。
- 源码补丁在生产基线副本上 `git apply --check` 通过。

本地首页使用明确标注的合成测试状态，不能用来证明生产登录、真实支付或下载包已验证。没有创建订单、发短信、录音、调用模型或部署；也不代表支付宝审核一定通过。

## 交付物

- [桌面首屏](../../design/previews/cn-homepage-layout/round2/desktop.png)
- [手机首屏](../../design/previews/cn-homepage-layout/round2/mobile.png)
- [完整页面](../../design/previews/cn-homepage-layout/round2/full-page.png)
- [源码差异补丁](../../design/previews/cn-homepage-layout/round2/source.patch)
- [限定源码与图片包](../../design/previews/cn-homepage-layout/round2/source-overlay.tgz)
- [仅本地预览支持包](../../design/previews/cn-homepage-layout/round2/preview-support.tgz)

补丁和源码包只针对匹配的生产基线，不应直接覆盖版本不同且存在未确认修改的主工作区。第一轮交付物保留。
