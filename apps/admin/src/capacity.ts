export type CapacityLevel = "healthy" | "warning" | "critical" | "unavailable";
export type CapacityPoint = { atMs: number; value: number | null };
export type CapacityMetric = {
  key: string;
  label: string;
  unit: string;
  value: number | null;
  warning: number | null;
  critical: number | null;
  level: CapacityLevel;
  description: string;
  points: CapacityPoint[];
};
export type RequestClassSummary = { requestCount: number; p95Ms: number; errorCount: number; errorRate: number };
export type SlowRouteDiagnostic = RequestClassSummary & { route: string; class: "user_api" | "telemetry" | "recovery_snapshot" | "sse_stream" };
export type RequestBreakdown = {
  classes: Partial<Record<"user_api" | "telemetry" | "recovery_snapshot" | "sse_stream", RequestClassSummary>>;
  slowRoutes: SlowRouteDiagnostic[];
  series?: Array<{ atMs: number; classes: Partial<Record<"user_api" | "telemetry" | "recovery_snapshot" | "sse_stream", number>> }>;
};
export type CapacityResponse = {
  generatedAtMs: number;
  sampleIntervalSeconds: number;
  windowMinutes: number;
  metrics: CapacityMetric[];
  supporting: {
    activeUsers: number | null;
    requestsPerMinute: number | null;
    databaseConnectionLimit: number | null;
    requestBreakdown?: RequestBreakdown;
  };
};

export const requestClassLabels: Record<keyof RequestBreakdown["classes"], string> = {
  user_api: "用户请求",
  telemetry: "后台遥测",
  recovery_snapshot: "恢复快照",
  sse_stream: "实时流",
};

export const hasRequestBreakdownData = (breakdown: RequestBreakdown | undefined): breakdown is RequestBreakdown => {
  return Boolean(breakdown);
};

export const formatCapacityValue = (value: number | null, unit: string): string => {
  if (value === null) return "暂无数据";
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "ms") return value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${Math.round(value)}ms`;
  if (unit === "s") return value >= 86_400 ? `${(value / 86_400).toFixed(1)} 天` : `${Math.round(value).toLocaleString("zh-CN")} 秒`;
  return `${Math.round(value).toLocaleString("zh-CN")} ${unit}`;
};

export const capacityLevelLabel: Record<CapacityLevel, string> = {
  healthy: "正常",
  warning: "需关注",
  critical: "接近容量",
  unavailable: "暂无数据",
};
