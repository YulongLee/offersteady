import { AppError, normalizeError } from "./domain";

interface JsonClientConfig {
  readonly baseUrl: string;
  readonly fetchImpl?: typeof fetch;
}

export class ApiResponseError extends Error {
  constructor(
    readonly status: number,
    readonly payload: unknown,
    message = `API request failed with status ${status}`,
  ) {
    super(message);
    this.name = "ApiResponseError";
  }
}

interface ApiEnvelope<T> {
  readonly success: boolean;
  readonly data: T | null;
  readonly error: {
    readonly code: string;
    readonly message: string;
    readonly details?: unknown;
  } | null;
  readonly requestId: string;
  readonly meta: {
    readonly apiVersion: string;
    readonly timestamp: string;
  };
}

const isEnvelope = <T>(payload: unknown): payload is ApiEnvelope<T> =>
  typeof payload === "object" &&
  payload !== null &&
  "success" in payload &&
  "requestId" in payload &&
  "meta" in payload;

const normalizeBaseUrl = (baseUrl: string) => baseUrl.replace(/\/+$/, "").replace(/\/api\/v1$/, "");

export const withBaseUrl = (baseUrl: string, path: string) => `${normalizeBaseUrl(baseUrl)}${path.startsWith("/") ? path : `/${path}`}`;

const defaultFetch: typeof fetch = (input, init) => globalThis.fetch(input, init);

export const createJsonClient = ({ baseUrl, fetchImpl = defaultFetch }: JsonClientConfig) => ({
  async request<T>(path: string, init?: RequestInit, signal?: AbortSignal): Promise<T> {
    let response: Response;
    const resolvedSignal = signal ?? init?.signal ?? null;
    const providedHeaders = new Headers(init?.headers);
    const shouldUseJsonContentType = typeof init?.body === "string" && !providedHeaders.has("Content-Type");
    const headers = {
      Accept: "application/json",
      ...(shouldUseJsonContentType ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    };
    try {
      response = await fetchImpl(withBaseUrl(baseUrl, path), {
        ...init,
        signal: resolvedSignal,
        headers,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      throw new AppError("network", "无法连接后端基础服务");
    }
    const payload = response.headers.get("content-type")?.includes("application/json") ? await response.json() : null;
    if (!response.ok) {
      if (isEnvelope<unknown>(payload) && payload.error?.message) {
        throw new AppError("validation", payload.error.message);
      }
      throw new ApiResponseError(response.status, payload);
    }
    if (isEnvelope<T>(payload)) {
      if (!payload.success || payload.data == null) {
        throw new AppError("validation", payload.error?.message ?? "后端返回了空结果");
      }
      return payload.data;
    }
    return payload as T;
  },
});

export const runAdapterOperation = async <T>(operation: (signal: AbortSignal) => Promise<T>, externalSignal?: AbortSignal): Promise<T> => {
  const controller = externalSignal ? null : new AbortController();
  try {
    return await operation(externalSignal ?? controller!.signal);
  } catch (error) {
    throw normalizeError(error);
  }
};
