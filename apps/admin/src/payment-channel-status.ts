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

const acceptanceOutcomes: Record<string, string> = {
  paid: "支付通知与权益到账均已通过",
  seller_identity_mismatch: "支付宝已通知付款，但 Seller ID 与配置的签约 PID 不一致。请从支付宝商户平台复制以 2088 开头的 16 位 PID，保存后重新执行权威查单。",
  app_identity_mismatch: "支付宝通知的应用 ID 与当前配置不一致，请核对收款应用和后台应用 ID。",
  invalid_signature: "通知签名校验失败，请核对当前应用对应的支付宝公钥。",
  amount_mismatch: "支付宝通知金额与本地订单金额不一致，订单未入账。",
  unknown_order: "支付宝通知中的商户订单号在本系统中不存在。",
  processing_failure: "通知已到达，但订单处理失败，请查看待对账订单并执行权威查单。",
  reconciled: "权威查单通过，订单与权益已完成入账。",
  already_reconciled: "订单此前已经完成对账，未重复发放权益。",
};

export const paymentAcceptanceOutcomeLabel = (outcome: unknown) => {
  const key = typeof outcome === "string" ? outcome : "";
  return acceptanceOutcomes[key] || (key ? `渠道返回：${key}` : "完成一次真实链路后显示");
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
