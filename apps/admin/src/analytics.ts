export type TrendPoint = { date: string; value: number | null; coverage: string };
export type TrendMetric = {
  key: string;
  label: string;
  unit: string;
  group: string;
  aggregation: string;
  description: string;
  backfillable: boolean;
  summary: { current: number | null; previous: number | null; changePercent: number | null };
  points: TrendPoint[];
};
export type TrendResponse = {
  range: "7d" | "30d" | "90d";
  timezone: string;
  startedOn: string;
  endedOn: string;
  generatedAtMs: number;
  metrics: TrendMetric[];
  health: { lastSuccessAtMs: number | null; coveredDays: number; latestRun: Record<string, unknown> | null };
};

export const buildLinePath = (points: TrendPoint[], width = 560, height = 150): string => {
  const values = points.map(point => point.value).filter((value): value is number => value !== null);
  if (!values.length) return "";
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const spread = Math.max(1, maximum - minimum);
  const step = points.length > 1 ? width / (points.length - 1) : width;
  let drawing = false;
  return points.map((point, index) => {
    if (point.value === null) {
      drawing = false;
      return "";
    }
    const x = index * step;
    const y = height - ((point.value - minimum) / spread) * (height - 16) - 8;
    const command = drawing ? "L" : "M";
    drawing = true;
    return `${command}${x.toFixed(1)},${y.toFixed(1)}`;
  }).filter(Boolean).join(" ");
};

export const formatTrendValue = (value: number | null, unit: string): string => {
  if (value === null) return "暂无数据";
  if (unit === "分") return `¥${(value / 100).toFixed(2)}`;
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "ms") return value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${Math.round(value)}ms`;
  return `${Math.round(value).toLocaleString("zh-CN")} ${unit}`;
};

export const formatTrendChange = (value: number | null): string =>
  value === null ? "暂无可比数据" : `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;

