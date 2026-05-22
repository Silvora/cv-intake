import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type CreateAxiosDefaults,
  type RawAxiosRequestHeaders,
} from 'axios';
import {
  QueryClient,
  type DefaultOptions,
  type MutationFunction,
  type MutationOptions,
  type QueryFunction,
  type QueryKey,
  type QueryOptions,
} from '@tanstack/query-core';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';
export type ResponseType = 'auto' | 'json' | 'text' | 'blob' | 'arrayBuffer' | 'stream';
export type RequestParams = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions
  extends Omit<
    AxiosRequestConfig,
    'url' | 'baseURL' | 'method' | 'headers' | 'params' | 'responseType' | 'timeout'
  > {
  headers?: RawAxiosRequestHeaders;
  params?: RequestParams;
  timeoutMs?: number;
  retry?: number;
  retryDelayMs?: number;
  retryOnStatuses?: number[];
  responseType?: ResponseType;
}

export interface ApiClientOptions {
  baseUrl: string;
  defaultHeaders?: RawAxiosRequestHeaders;
  getAccessToken?: () => string | null | Promise<string | null>;
  onUnauthorized?: (error: HttpError) => void | Promise<void>;
  timeoutMs?: number;
  retry?: number;
  retryDelayMs?: number;
  retryOnStatuses?: number[];
}

export interface ApiRequestConfig extends RequestOptions {
  method: HttpMethod;
  path: string;
  url: string;
}

export interface ApiResponse<T = unknown> {
  data: T;
  response: AxiosResponse<T>;
  request: ApiRequestConfig;
}

export class HttpError extends Error {
  readonly status: number;
  readonly data: unknown;
  readonly headers: RawAxiosRequestHeaders;
  readonly url: string;
  readonly method: HttpMethod;

  constructor(args: {
    message: string;
    status: number;
    data: unknown;
    headers: RawAxiosRequestHeaders;
    url: string;
    method: HttpMethod;
  }) {
    super(args.message);
    this.name = 'HttpError';
    this.status = args.status;
    this.data = args.data;
    this.headers = args.headers;
    this.url = args.url;
    this.method = args.method;
  }
}

function toAxiosResponseType(responseType?: ResponseType): AxiosRequestConfig['responseType'] | undefined {
  if (!responseType || responseType === 'auto') return undefined;
  if (responseType === 'arrayBuffer') return 'arraybuffer';
  return responseType;
}

function normalizeParams(params?: RequestParams) {
  if (!params) return undefined;
  const next: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      next[key] = value;
    }
  }
  return next;
}

function toPlainHeaders(headers: unknown): RawAxiosRequestHeaders {
  if (!headers) return {};
  if (headers instanceof AxiosHeaders) {
    return headers.toJSON() as RawAxiosRequestHeaders;
  }
  return headers as RawAxiosRequestHeaders;
}

export class ApiClient {
  private readonly instance: AxiosInstance;
  private readonly getAccessToken?: () => string | null | Promise<string | null>;
  private readonly onUnauthorized?: (error: HttpError) => void | Promise<void>;
  private readonly timeoutMs: number;
  private readonly retry: number;
  private readonly retryDelayMs: number;
  private readonly retryOnStatuses: number[];

  readonly interceptors: AxiosInstance['interceptors'];

  constructor(options: ApiClientOptions) {
    this.instance = axios.create({
      baseURL: options.baseUrl.replace(/\/$/, ''),
      headers: options.defaultHeaders,
      timeout: options.timeoutMs ?? 15_000,
    } satisfies CreateAxiosDefaults);

    this.interceptors = this.instance.interceptors;
    this.getAccessToken = options.getAccessToken;
    this.onUnauthorized = options.onUnauthorized;
    this.timeoutMs = options.timeoutMs ?? 15_000;
    this.retry = options.retry ?? 0;
    this.retryDelayMs = options.retryDelayMs ?? 500;
    this.retryOnStatuses = options.retryOnStatuses ?? [408, 425, 429, 500, 502, 503, 504];
  }

  get<T>(path: string, options: RequestOptions = {}) {
    return this.request<T>('GET', path, options);
  }

  post<T>(path: string, body?: unknown, options: RequestOptions = {}) {
    return this.request<T>('POST', path, { ...options, data: body });
  }

  put<T>(path: string, body?: unknown, options: RequestOptions = {}) {
    return this.request<T>('PUT', path, { ...options, data: body });
  }

  patch<T>(path: string, body?: unknown, options: RequestOptions = {}) {
    return this.request<T>('PATCH', path, { ...options, data: body });
  }

  delete<T>(path: string, options: RequestOptions = {}) {
    return this.request<T>('DELETE', path, options);
  }

  createAbortController() {
    return new AbortController();
  }

  async request<T>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
    const request = await this.buildRequestConfig(method, path, options);
    return this.dispatch<T>(request);
  }

  private async buildRequestConfig(
    method: HttpMethod,
    path: string,
    options: RequestOptions,
  ): Promise<ApiRequestConfig> {
    const token = this.getAccessToken ? await this.getAccessToken() : null;
    const headers = new AxiosHeaders(options.headers as AxiosHeaders);
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    return {
      ...options,
      method,
      path,
      url: path,
      headers: headers.toJSON() as RawAxiosRequestHeaders,
      params: normalizeParams(options.params),
      timeoutMs: options.timeoutMs ?? this.timeoutMs,
      responseType: options.responseType ?? 'auto',
    };
  }

  private async dispatch<T>(request: ApiRequestConfig): Promise<T> {
    const maxRetries = request.retry ?? this.retry;
    for (let attempt = 0; ; attempt += 1) {
      try {
        const response = await this.instance.request<T>({
          ...request,
          method: request.method,
          url: request.url,
          headers: request.headers,
          params: request.params,
          timeout: request.timeoutMs,
          responseType: toAxiosResponseType(request.responseType),
        });
        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError;
        const status = axiosError.response?.status;
        if (status === 401 && this.onUnauthorized) {
          await this.onUnauthorized(this.toHttpError(axiosError, request));
        }

        const shouldRetry = this.shouldRetry(axiosError, request, attempt, maxRetries);
        if (shouldRetry) {
          await this.delay(this.resolveRetryDelay(request, attempt));
          continue;
        }
        throw this.toHttpError(axiosError, request);
      }
    }
  }

  private shouldRetry(
    error: AxiosError,
    request: ApiRequestConfig,
    attempt: number,
    maxRetries: number,
  ) {
    if (attempt >= maxRetries) {
      return false;
    }
    if (!error.response) {
      return true;
    }
    const retryStatuses = request.retryOnStatuses ?? this.retryOnStatuses;
    return retryStatuses.includes(error.response.status);
  }

  private resolveRetryDelay(request: ApiRequestConfig, attempt: number) {
    const base = request.retryDelayMs ?? this.retryDelayMs;
    return base * (attempt + 1);
  }

  private delay(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private toHttpError(error: AxiosError, request: ApiRequestConfig): HttpError {
    const status = error.response?.status ?? 0;
    return new HttpError({
      message: error.message || `Request failed with status ${status}`,
      status,
      data: error.response?.data,
      headers: toPlainHeaders(error.response?.headers),
      url: request.url,
      method: request.method,
    });
  }
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  return new ApiClient(options);
}

export function createQueryClient(defaultOptions?: DefaultOptions): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        retry: 1,
      },
      ...defaultOptions,
    },
  });
}

export function createScopedQueryKeys(scope: string) {
  return {
    all: [scope] as const,
    detail: (id: string | number) => [scope, 'detail', id] as const,
    list: (filters?: Record<string, unknown>) => [scope, 'list', filters ?? {}] as const,
  };
}

export function createApiQueryOptions<TData>(key: QueryKey, queryFn: () => Promise<TData>) {
  return {
    queryKey: key,
    queryFn: queryFn as QueryFunction<TData>,
  } satisfies QueryOptions<TData, Error, TData, QueryKey>;
}

export function createApiMutationOptions<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  return {
    mutationFn: mutationFn as MutationFunction<TData, TVariables>,
  } satisfies MutationOptions<TData, Error, TVariables>;
}
