const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "";

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface RequestOptions {
  timeoutMs?: number;
  redirectOnUnauthorized?: boolean;
}

function stringifyValidationDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return null;

  const messages = detail
    .map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        return String((item as { msg: unknown }).msg);
      }
      return "";
    })
    .filter(Boolean);

  return messages.length > 0 ? messages.join("；") : null;
}

function extractMessageFromJson(parsed: unknown): string | null {
  if (!parsed || typeof parsed !== "object") return null;

  const payload = parsed as {
    detail?: unknown;
    message?: unknown;
    error?: unknown;
  };

  const detail = stringifyValidationDetail(payload.detail);
  if (detail) return detail;
  if (typeof payload.message === "string" && payload.message.trim()) {
    return payload.message;
  }
  if (typeof payload.error === "string" && payload.error.trim()) {
    return payload.error;
  }
  if (
    payload.error &&
    typeof payload.error === "object" &&
    "message" in payload.error &&
    typeof (payload.error as { message: unknown }).message === "string"
  ) {
    return String((payload.error as { message: unknown }).message);
  }

  return null;
}

async function extractApiErrorMessage(response: Response, fallback: string): Promise<string> {
  const text = await response.text();
  if (!text.trim()) return fallback;

  try {
    const parsed = JSON.parse(text) as unknown;
    return extractMessageFromJson(parsed) || text;
  } catch {
    return text;
  }
}

function isAbortError(error: unknown): boolean {
  return (
    error instanceof Error &&
    (error.name === "AbortError" || error.message.includes("aborted"))
  );
}

async function request<T>(
  method: string,
  url: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  const timeoutMs = options.timeoutMs ?? (method === "GET" ? 15000 : undefined);
  const controller = timeoutMs && timeoutMs > 0 ? new AbortController() : null;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  let response: Response;
  try {
    if (controller && timeoutMs) {
      timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    }

    response = await fetch(fullUrl, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      credentials: "include",
      signal: controller?.signal,
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw new Error("请求超时，请稍后重试");
    }
    throw error;
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }

  if (response.status === 401) {
    const message = await extractApiErrorMessage(response, "Unauthorized");
    if (options.redirectOnUnauthorized !== false && typeof window !== "undefined") {
      const current = window.location.pathname;
      if (!current.startsWith("/login")) {
        const redirect =
          current !== "/"
            ? `?redirect=${encodeURIComponent(current)}`
            : "";
        window.location.href = `/login${redirect}`;
      }
    }
    throw new Error(message);
  }

  if (!response.ok) {
    const message = await extractApiErrorMessage(response, `HTTP ${response.status}`);
    throw new Error(message);
  }

  const json = (await response.json()) as ApiResponse<T>;
  if (json && json.success === false) {
    throw new Error(json.message || "请求失败");
  }
  return json.data;
}

export const api = {
  get: <T>(url: string, options?: RequestOptions) => request<T>("GET", url, undefined, options),
  post: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>("POST", url, body, options),
  put: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PUT", url, body, options),
  patch: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PATCH", url, body, options),
  delete: <T>(url: string, options?: RequestOptions) => request<T>("DELETE", url, undefined, options),
};
