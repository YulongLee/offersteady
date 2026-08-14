export interface GrowthSettingsValidation {
  readonly valid: boolean;
  readonly message: string;
}

export function validateGrowthSettings(inviterRewardPoints: string, inviteeRewardPoints: string, reason: string): GrowthSettingsValidation {
  const inviterPoints = Number(inviterRewardPoints);
  if (!Number.isInteger(inviterPoints) || inviterPoints < 1 || inviterPoints > 100000) {
    return { valid: false, message: "分享者奖励必须是 1–100000 的整数。" };
  }
  const inviteePoints = Number(inviteeRewardPoints);
  if (!Number.isInteger(inviteePoints) || inviteePoints < 1 || inviteePoints > 100000) {
    return { valid: false, message: "新用户奖励必须是 1–100000 的整数。" };
  }
  if (reason.trim().length < 3) {
    return { valid: false, message: "请填写至少 3 个字的配置变更原因。" };
  }
  return { valid: true, message: "" };
}
