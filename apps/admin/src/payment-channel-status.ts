export type PaymentChannelStatusInput = {
  enabled?: unknown;
  validationStatus?: unknown;
  validationErrors?: unknown;
  updatedAtMs?: unknown;
};

export type PaymentChannelStatus = {
  active: boolean;
  ready: boolean;
  usageLabel: "用户端正在使用" | "用户端未使用";
  usageDescription: string;
  readinessLabel: "配置可启用" | "配置待完善";
  readinessDescription: string;
  validationErrors: string[];
  updatedAtLabel: string;
};

export function paymentChannelStatus(row: PaymentChannelStatusInput): PaymentChannelStatus {
  const ready = row.validationStatus === "ready";
  const active = row.enabled === true && ready;
  const validationErrors = Array.isArray(row.validationErrors)
    ? row.validationErrors.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
  const updatedAtMs = typeof row.updatedAtMs === "number" ? row.updatedAtMs : Number(row.updatedAtMs);

  return {
    active,
    ready,
    usageLabel: active ? "用户端正在使用" : "用户端未使用",
    usageDescription: active
      ? "用户支付页现在可以选择此支付方式；仍需完成真实小额支付验收。"
      : "用户支付页当前不会显示此支付方式，也不会通过此渠道创建新订单。",
    readinessLabel: ready ? "配置可启用" : "配置待完善",
    readinessDescription: ready
      ? "必填字段和密钥格式已通过静态校验，但不代表真实支付已经验收。"
      : "请修正下方配置问题并重新保存，校验通过后才能开启。",
    validationErrors,
    updatedAtLabel: Number.isFinite(updatedAtMs) && updatedAtMs > 0
      ? new Date(updatedAtMs).toLocaleString("zh-CN")
      : "尚未更新",
  };
}
