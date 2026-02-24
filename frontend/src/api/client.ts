export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      ...options?.headers,
    },
  });

  if (response.status === 401) {
    throw new ApiError("UNAUTHORIZED", "Unauthorized", 401);
  }

  const data = await response.json();

  if (!response.ok || data.success === false) {
    throw new ApiError(
      data.error?.code || "UNKNOWN",
      data.error?.message || "Request failed",
      response.status
    );
  }

  return data.data !== undefined ? data.data : data;
}

export function get<T>(url: string): Promise<T> {
  return request<T>(url);
}

export function post<T>(url: string, body?: unknown): Promise<T> {
  return request<T>(url, {
    method: "POST",
    headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function patch<T>(url: string, body: unknown): Promise<T> {
  return request<T>(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function del<T>(url: string): Promise<T> {
  return request<T>(url, { method: "DELETE" });
}

export async function fetchMessage(
  url: string,
  options?: RequestInit
): Promise<string> {
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: { ...options?.headers },
  });

  if (response.status === 401) {
    throw new ApiError("UNAUTHORIZED", "Unauthorized", 401);
  }

  const data = await response.json();

  if (!response.ok || data.success === false) {
    throw new ApiError(
      data.error?.code || "UNKNOWN",
      data.error?.message || "Request failed",
      response.status
    );
  }

  return data.message || "";
}
