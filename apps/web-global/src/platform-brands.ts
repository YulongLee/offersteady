export interface PlatformBrand {
  readonly slug: string;
  readonly name: string;
  readonly logoUrl: string;
  readonly sourcePage: string;
  readonly presentation: "wordmark" | "lockup";
  readonly secondaryLabel?: string;
}

// Product marks remain the property of their respective owners. These URLs point
// to the owners' public product sites or asset CDNs and are used only to identify
// common compatibility scenarios, not to imply endorsement or partnership.
export const interviewPlatforms: readonly PlatformBrand[] = [
  { slug: "zoom", name: "Zoom", logoUrl: "https://st1.zoom.us/homepage/20260805-1234/primary/dist/assets/zoommedia/logo-zoom@2x.png", sourcePage: "https://zoom.us/", presentation: "wordmark" },
  { slug: "google-meet", name: "Google Meet", logoUrl: "https://fonts.gstatic.com/s/i/productlogos/meet_2020q4/v8/192px.svg", sourcePage: "https://about.google/brand-resource-center/", presentation: "lockup" },
  { slug: "teams", name: "Microsoft Teams", logoUrl: "https://teams.public.onecdn.static.microsoft/evergreen-assets/icons/microsoft_teams_logo_refresh_v2025.ico", sourcePage: "https://www.microsoft.com/legal/intellectualproperty/trademarks", presentation: "lockup" },
  { slug: "tencent-meeting", name: "腾讯会议", logoUrl: "https://cdn.meeting.tencent.com/assets/next-website/logo128.png", sourcePage: "https://meeting.tencent.com/", presentation: "lockup", secondaryLabel: "Tencent Meeting" },
  { slug: "feishu", name: "飞书", logoUrl: "https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/84a9f036fe2b44f99b899fff4beeb963~tplv-jbbdkfciu3-image:100:100.image", sourcePage: "https://www.feishu.cn/", presentation: "lockup" },
  { slug: "dingtalk", name: "钉钉", logoUrl: "https://img.alicdn.com/imgextra/i3/O1CN017PqYP51OX3bSJGxQY_!!6000000001714-2-tps-200-200.png", sourcePage: "https://www.dingtalk.com/", presentation: "lockup" },
  { slug: "wecom", name: "企业微信", logoUrl: "https://wwcdn.weixin.qq.com/node/wwnl/wwnl/style/images/independent/favicon/favicon_48h$c976bd14.png", sourcePage: "https://work.weixin.qq.com/", presentation: "lockup" },
  { slug: "leetcode", name: "力扣", logoUrl: "https://leetcode.com/favicon.ico", sourcePage: "https://leetcode.com/", presentation: "lockup", secondaryLabel: "LeetCode" },
  { slug: "nowcoder", name: "牛客", logoUrl: "https://static.nowcoder.com/fe/common/share-logo.png", sourcePage: "https://www.nowcoder.com/", presentation: "lockup", secondaryLabel: "NOWCODER" },
  { slug: "slack", name: "Slack", logoUrl: "https://a.slack-edge.com/e6a93c1/img/icons/favicon-32.png", sourcePage: "https://slack.com/", presentation: "lockup" },
] as const;
