export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function sendRequest(url: string, options?: RequestInit): Promise<Response> {
  return fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      ...options?.headers,
    },
  });
}

async function createApiError(response: Response): Promise<ApiError> {
  if (response.status === 401) {
    return new ApiError("UNAUTHORIZED", "Unauthorized", 401);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const data = await response.json();
    return new ApiError(
      data.error?.code || "UNKNOWN",
      data.error?.message || "Request failed",
      response.status
    );
  }

  return new ApiError("UNKNOWN", "Request failed", response.status);
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await sendRequest(url, options);

  if (!response.ok) {
    throw await createApiError(response);
  }

  const data = await response.json();

  if (data.success === false) {
    throw new ApiError(
      data.error?.code || "UNKNOWN",
      data.error?.message || "Request failed",
      response.status
    );
  }

  return data.data !== undefined ? data.data : data;
}

async function requestVoid(url: string, options?: RequestInit): Promise<void> {
  const response = await sendRequest(url, options);

  if (!response.ok) {
    throw await createApiError(response);
  }
}

function buildBodyOptions(body?: unknown): Pick<RequestInit, "headers" | "body"> {
  return {
    headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  };
}

export function get<T>(url: string): Promise<T> {
  return request<T>(url);
}

export function post<T>(url: string, body?: unknown): Promise<T> {
  return request<T>(url, {
    method: "POST",
    ...buildBodyOptions(body),
  });
}

export function postVoid(url: string, body?: unknown): Promise<void> {
  return requestVoid(url, {
    method: "POST",
    ...buildBodyOptions(body),
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
  const response = await sendRequest(url, options);

  if (!response.ok) {
    throw await createApiError(response);
  }

  const data = await response.json();

  if (data.success === false) {
    throw new ApiError(
      data.error?.code || "UNKNOWN",
      data.error?.message || "Request failed",
      response.status
    );
  }

  return data.message || "";
}
