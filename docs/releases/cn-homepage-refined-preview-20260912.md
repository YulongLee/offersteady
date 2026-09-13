# 国服首页排版修正版（本地）

版本：`cn-homepage-refined-20260912.local`。

预览：<http://127.0.0.1:5187/>。继续运行原本地预览服务，未部署国服或国际服，未修改 `.env`、后端、登录、计费或支付。

## 已完成

依据用户确认的视觉复查意见，在既有深色绿色品牌与隔离生产副本上实施限定优化；Product Design 的上下文与视觉审查规则用于保持原有风格、检查实机呈现，没有引入新模板。

- 首屏改为更紧凑的标题和等宽双栏；原截图聚焦右侧回答区，保留完整图片链接并明确局部展示。原图片未修改。
- 三步说明并入视频侧栏，减少重复占位；两段原视频和公开手册入口保留，不自动播放。
- 五档会员改为紧凑的时长选择，统一显示所选金额、有效期与知识材料额度。全部有效目录项仍可见；选择无效时从当前目录安全回退，不保留旧套餐快照。
- 积分费率继续读现有配置；保留知识材料额外消耗、并发/防滥用边界和订单支持入口。
- 岗位区直接展示技术岗位、实时辅助、面试指南三个已有页面入口，完整岗位与平台内容仍可展开。
- FAQ 改为左侧介绍、右侧问题列表；合作伙伴降为次级文字入口，原条件、推广说明和链接保留。
- 清理此前首页样式叠加，统一章节字号、正文可读性和响应式间距；所有样式限制在国服首页。

## 修改位置

业务项目的主工作区已有未确认修改保留。实现位于 `artifacts/cn-homepage-layout.82qdGV/candidate`：

| 文件 | 用途 |
| --- | --- |
| `apps/web/src/App.tsx` | 国服首页布局、教程、岗位和页尾层级 |
| `apps/web/src/HomepagePricing.tsx` | 新增纯展示的目录驱动套餐选择 |
| `apps/web/src/HomepageProductPreview.tsx` | 明确真实截图局部展示 |
| `apps/web/src/homepage-commercial.css` | 首页视觉和响应式样式 |
| `apps/web/index.html` | 初始 HTML 核心正文与现有内链同步 |
| `apps/web/src/homepage-layout.test.tsx` | 14 项展示与边界回归 |
| `apps/web/vite.layout-preview.config.ts` | 仅本地映射已有公开页面，排除于正式源码补丁 |

## 验证

- `npm run typecheck`：通过。
- 生产模式 `npm run build`：通过；最终主 JS 452.78 kB / gzip 135.19 kB，CSS 126.89 kB / gzip 23.02 kB。未放宽体积阈值。
- `node scripts/verify-pricing-live.mjs`：通过，构建目录与当时生产 10 个商品一致，快照小于 24 小时。
- 首页 14/14 通过。包含选择全部套餐、动态费率、无效/下架/空目录、知识材料额度联动、下载菜单、公开价格、初始 HTML 和新内链。
- Web 全量 387 项：377 通过，10 失败。与第二轮/生产基线的失败名称对比无新增；不是全量绿灯。原失败涉及历史首页断言、合作伙伴入口断言和资料错误提示。
- 浏览器检查：320、390、900、1440 px 均无横向溢出。320 px 两个下载按钮为 138×48，会员按钮约 76.7×68；390 px 下载按钮为 173×48，会员按钮为 100×68。
- 320 px 的 Mac 菜单左右范围 104–304，未超视口；Escape 正常关闭。
- 实际点击 30 天并键盘切回 1 天，金额和知识材料权益对应正确，单一选中状态正常。
- 实际切换项目/截图示例、展开费用 FAQ、进入公开价格页并返回，正常；本轮浏览器错误日志为空。
- 本地首页、价格、两个核心功能页、指南和两张图片均返回 200。没有对生产做负载或写入测试。
- 基于生产副本的限定补丁 `git apply --check` 通过；OpenSpec 严格校验通过。

本地顶部提示及合成测试状态仅用于排版预览。没有创建真实订单、安装下载包或验证真实登录/支付；没有保证审核或转化结果。

## 交付

- [桌面首屏](../../design/previews/cn-homepage-layout/round3/desktop-hero.png)
- [手机首屏](../../design/previews/cn-homepage-layout/round3/mobile-hero.png)
- [桌面整页](../../design/previews/cn-homepage-layout/round3/desktop-full.png)
- [手机整页](../../design/previews/cn-homepage-layout/round3/mobile-full.png)
- [累计源码补丁](../../design/previews/cn-homepage-layout/round3/source.patch)
- [源码与原有图片包](../../design/previews/cn-homepage-layout/round3/source-overlay.tgz)
- [仅本地预览支持包](../../design/previews/cn-homepage-layout/round3/preview-support.tgz)

上一轮 `round2` 完整交付物保留，可恢复本地预览。累计补丁仅针对对应生产基线，不应覆盖版本不同且含用户修改的主工作区。后续发布需要另行确认。
