export interface GrowthSettingsValidation {
  readonly valid: boolean;
  readonly message: string;
}

export function validateGrowthSettings(rewardPoints: string, reason: string): GrowthSettingsValidation {
  const points = Number(rewardPoints);
  if (!Number.isInteger(points) || points < 1 || points > 100000) {
    return { valid: false, message: "单次奖励必须是 1–100000 的整数。" };
  }
  if (reason.trim().length < 3) {
    return { valid: false, message: "请填写至少 3 个字的配置变更原因。" };
  }
  return { valid: true, message: "" };
}
