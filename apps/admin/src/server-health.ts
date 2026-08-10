import type { CapacityMetric } from "./capacity";

export type DependencyHealth = {
  key: string;
  label: string;
  status: "healthy" | "warning" | "critical" | "unavailable";
  latencyMs: number | null;
  detail: string;
};

export type ServerHealthResponse = {
  generatedAtMs: number;
  sampleIntervalSeconds: number;
  windowMinutes: number;
  overall: "healthy" | "warning" | "critical";
  resources: CapacityMetric[];
  dependencies: DependencyHealth[];
  supporting: { uptimeSeconds: number | null; requestsPerMinute: number | null };
};

export const formatUptime = (seconds: number | null | undefined) => {
  if (seconds === null || seconds === undefined) return "—";
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  return days ? `${days} 天 ${hours} 小时` : `${hours} 小时`;
};

