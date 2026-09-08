# 交付验证

- 成片：`out/offersteady-hangla-price-cn.mp4`
- 无 BGM：`out/offersteady-hangla-price-cn-nobgm.mp4`
- 时长：45.056 秒
- 画面：1080 × 1920，H.264，30fps
- 音频：AAC；BGM 版整体均值 -19.1dB、峰值 -0.7dB
- 黑帧检查：未检出持续 0.2 秒以上的黑帧段
- 两版画面：逐帧 MD5 一致
- 两版音频：MD5 不同，确认 `bgm` 开关生效；无 BGM 版保留旁白与 SFX
- 面试稳公开价格证据：`docs/audits/cn-core-seo-20260908/after-_pricing-baidu.html`（生产商品目录快照，¥29.90/1天、会员期内实时面试/回答/截图不扣积分）
- 面试稳生产结算证据：`apps/backend/migrations/versions/0018_admin_managed_billing_catalog.sql:30`（`pass-1`、2990 分、1 天），`apps/web/src/BillingPage.tsx:475`（回答与截图不限次）
- 敏感信息：画面和旁白未包含 API Key、Token、服务器地址、用户数据或内部性能指标

竞品价格采集日期为 2026-09-08，来源和口径见 `design-spec.md`。发布前如官网价格变化，应重新核对并更新画面。
