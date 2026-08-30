## Why

面试稳已经取得公安联网备案号，但公开首页当前只展示 ICP 备案号，缺少公安备案信息。需要在首页底部显著展示并链接官方查询页面，使线上展示与已完成的备案状态一致。

## What Changes

- 在公开首页最底部展示“浙公网安备33010602014812号”。
- 将公安备案号链接到公安机关互联网安全管理平台对应备案记录，并以新窗口安全打开。
- 保留现有 ICP 备案号、版权信息和响应式页脚布局。
- 增加前端回归测试，防止备案号或官方链接在后续首页调整中丢失。

## Capabilities

### New Capabilities

- `public-security-filing-footer`: 规定公开首页底部展示公安联网备案号及官方查询链接。

### Modified Capabilities

无。

## Impact

- `apps/web/src/App.tsx`：公开首页页脚备案信息。
- `apps/web/src/styles.css`：备案链接在桌面端和移动端的排列。
- `apps/web/src/App.product-experience.test.tsx`：首页备案展示回归测试。
- `apps/web/public/public-facts.json`：公开产品事实中的公安备案信息。
- 不涉及后端 API、用户数据、音频或个人资料处理。
