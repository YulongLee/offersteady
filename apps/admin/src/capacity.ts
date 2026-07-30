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
export type CapacityResponse = {
  generatedAtMs: number;
  sampleIntervalSeconds: number;
  windowMinutes: number;
  metrics: CapacityMetric[];
  supporting: {
    activeUsers: number | null;
    requestsPerMinute: number | null;
    databaseConnectionLimit: number | null;
  };
};

export const formatCapacityValue = (value: number | null, unit: string): string => {
  if (value === null) return "暂无数据";
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "ms") return value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${Math.round(value)}ms`;
  return `${Math.round(value).toLocaleString("zh-CN")} ${unit}`;
};

export const capacityLevelLabel: Record<CapacityLevel, string> = {
  healthy: "正常",
  warning: "需关注",
  critical: "接近容量",
  unavailable: "暂无数据",
};
