# 面试稳 · 官网商业宣传片

36 秒中文产品演示，1920×1080 / 60 fps。独立视频工程，未修改或部署产品网页。

## 交付文件

- `out/offersteady-commercial.mp4`：高清成片，音乐 + 音效。
- `out/offersteady-commercial-nobgm.mp4`：同一画面时间线，仅保留音效，方便后期配乐。
- `out/web/offersteady-web.mp4`：1080p / 30fps 无音轨网页版，H.264、4:2:0、faststart。
- `out/web/offersteady-web-720.mp4`：720p / 30fps 无音轨备选。
- `out/web/poster.jpg`：网页封面。
- `out/offersteady-website-video.zip`：高清版、仅音效版、网页版、封面、嵌入与来源说明的交付包。
- `out/web/index.html`：可直接打开的播放预览。
- `final-review.md`、`verification.md`：独立审查与编码/音频验证。

## 网页嵌入

上传 `out/web/` 中的 MP4 与封面，然后替换路径：

```html
<video
  controls muted playsinline preload="metadata"
  poster="/videos/offersteady/poster.jpg"
  width="1920" height="1080"
  aria-label="面试稳产品功能演示"
  style="display:block;width:100%;height:auto;border-radius:20px;background:#080c13"
>
  <source src="/videos/offersteady/offersteady-web.mp4" type="video/mp4">
  你的浏览器不支持视频播放，请下载视频观看。
</video>
```

首屏若需要循环自动播放，可以增加 `autoplay loop`，保留 `muted playsinline`。应给减少动态效果偏好的用户保留静态封面或手动播放，页面出视口后暂停。首屏不要预加载高清音乐母版；网页文件已经移除音轨并设置 faststart。字幕已烧录，静音可理解内容。正文截图是辅助示例，主要叙事由大字文案承担。

## 工程与复现

- 当前使用已有视频工程的相同版本依赖，`node_modules` 是本机复用链接；迁移工程时不复制这个链接，使用本目录的锁文件独立执行 `npm ci`。
- `npm run dev`：Remotion 预览。
- `npm run typecheck`：TypeScript 检查。
- `npm run render`：渲染音乐版。
- `npm run render:nobgm`：渲染仅音效版。
- `npm run qa`：渲染关键静帧。
- 使用 Remotion 下载的 Chrome Headless Shell 149；本机完整 Chrome 152 的整片渲染出现超时，静帧可以工作，不推荐用于整片导出。
- 素材来自当前产品的真实 React/CSS，通过 `capture-vite.config.ts` 使用合成 fixture。采集配置与合成数据不参与业务构建。
- 从仓库根启动采集服务：`node_modules/.bin/vite apps/web --config video/offersteady-web-commercial/capture-vite.config.ts --host 127.0.0.1 --port 5187`。
- 从仓库根执行采集：`node video/offersteady-web-commercial/capture-product.mjs`。
- 合成素材已固定在 `public/textures/`；普通重渲无需启动产品服务。
- `reference/` 是制作审查用参考文件，不应上传官网，也不随网页交付包发布。

## 素材来源

面试稳图标与页面：本仓库。题目、资料与答案：合成示例。参考片只用于运镜分析，未将竞品视频、人物、标识或界面放入成片。

音乐为 Arulo 的 Cat Walk，来自 [Mixkit House 曲库](https://mixkit.co/free-stock-music/house/)，文件来源 `https://assets.mixkit.co/music/371/371.mp3`。音效来自 video-shotcraft 收录的 Mixkit 素材；逐项记录在 [音频来源](public/audio/ATTRIBUTION.md)。[Mixkit 授权](https://mixkit.co/license/)原始页面快照保存在 reference，仅用于本次来源核验。
