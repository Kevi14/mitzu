const BASE_URL = "/api";

type FetchOptions = RequestInit & { json?: unknown };

async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { json, ...init } = options;

  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };

  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(json);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include", // sends httpOnly cookie
  });

  if (response.status === 401) {
    window.location.href = "/login";
    return Promise.reject(new Error("Unauthenticated"));
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>;
  }
  return null as T;
}

export const api = {
  get: <T>(path: string, init?: RequestInit) => request<T>(path, { method: "GET", ...init }),
  post: <T>(path: string, json?: unknown) => request<T>(path, { method: "POST", json }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
