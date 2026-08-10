export type RevenueCategory = { count: number; amountCents: number };

export type PaymentRevenueSummary = {
  timezone: string;
  startedAtMs: number;
  endsAtMs: number;
  generatedAtMs: number;
  source: "live_orders";
  paid: RevenueCategory;
  pending: RevenueCategory;
  anomalous: RevenueCategory;
  closed: RevenueCategory;
};

export const formatCny = (amountCents: number | null | undefined) =>
  `¥${((amountCents || 0) / 100).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const diagnosticLabel = (value: unknown) => value === true ? "通过" : value === false ? "失败" : "未检查";

