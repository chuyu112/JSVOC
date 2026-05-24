const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "";

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
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

async function request<T>(
  method: string,
  url: string,
  body?: unknown,
): Promise<T> {
  const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };

  const response = await fetch(fullUrl, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "include",
  });

  if (response.status === 401) {
    const message = await extractApiErrorMessage(response, "Unauthorized");
    if (typeof window !== "undefined") {
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
  get: <T>(url: string) => request<T>("GET", url),
  post: <T>(url: string, body?: unknown) => request<T>("POST", url, body),
  put: <T>(url: string, body?: unknown) => request<T>("PUT", url, body),
  patch: <T>(url: string, body?: unknown) => request<T>("PATCH", url, body),
  delete: <T>(url: string) => request<T>("DELETE", url),
};
