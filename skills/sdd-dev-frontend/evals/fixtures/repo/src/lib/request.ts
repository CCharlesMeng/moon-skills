const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

const ERROR_MESSAGES: Record<string, string> = {
  AUTH_EXPIRED: '登录已过期，请重新登录',
  TENANT_FORBIDDEN: '当前租户无权访问该数据',
  RATE_LIMITED: '请求过于频繁，请稍后再试',
  UPSTREAM_TIMEOUT: '数据源响应超时，请稍后重试',
};

export class RequestError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, status: number) {
    super(ERROR_MESSAGES[code] ?? '请求失败，请稍后重试');
    this.name = 'RequestError';
    this.code = code;
    this.status = status;
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  signal?: AbortSignal;
}

/**
 * 全仓唯一的请求出口。所有后端调用都必须经过这里：
 * 它统一挂鉴权头与租户头、把后端错误码翻成用户可读文案、透传取消信号。
 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getAccessToken()}`,
      'X-Tenant-Id': import.meta.env.VITE_TENANT_ID ?? '',
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { code?: string };
    throw new RequestError(payload.code ?? 'UNKNOWN', response.status);
  }

  return (await response.json()) as T;
}

function getAccessToken(): string {
  return window.sessionStorage.getItem('access_token') ?? '';
}
