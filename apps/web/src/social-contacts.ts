export interface OfficialSocialContact {
  readonly id: "douyin" | "xiaohongshu";
  readonly label: "抖音号" | "小红书号";
  readonly account: "面试稳AI助手";
}

export const officialSocialContacts = [
  { id: "douyin", label: "抖音号", account: "面试稳AI助手" },
  { id: "xiaohongshu", label: "小红书号", account: "面试稳AI助手" },
] as const satisfies readonly OfficialSocialContact[];
