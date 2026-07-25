import type { ApiErrorBody, ApiErrorResponse } from '../types/api';

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

export class ApiClientError extends Error {
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly requestId: string;
  readonly status: number;
  readonly kind: 'api' | 'network' | 'parse';

  constructor(options: {
    message: string;
    code: string;
    details?: Record<string, unknown>;
    requestId?: string;
    status?: number;
    kind?: 'api' | 'network' | 'parse';
  }) {
    super(options.message);
    this.name = 'ApiClientError';
    this.code = options.code;
    this.details = options.details ?? {};
    this.requestId = options.requestId ?? '';
    this.status = options.status ?? 0;
    this.kind = options.kind ?? 'api';
  }
}

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  if (!configured) {
    return DEFAULT_BASE_URL;
  }
  return configured.replace(/\/$/, '');
}

function createRequestId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 24);
  }
  return `req_${Date.now().toString(36)}`;
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const error = (value as ApiErrorResponse).error;
  return (
    !!error &&
    typeof error === 'object' &&
    typeof error.code === 'string' &&
    typeof error.message === 'string'
  );
}

async function parseErrorResponse(
  response: Response,
  fallbackRequestId: string,
): Promise<ApiClientError> {
  const requestIdHeader = response.headers.get('X-Request-ID') ?? fallbackRequestId;
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    return new ApiClientError({
      message: `Request failed with status ${response.status}`,
      code: 'HTTP_ERROR',
      requestId: requestIdHeader,
      status: response.status,
      kind: 'parse',
    });
  }

  if (isApiErrorResponse(payload)) {
    const body: ApiErrorBody = payload.error;
    return new ApiClientError({
      message: body.message,
      code: body.code,
      details: body.details ?? {},
      requestId: body.request_id || requestIdHeader,
      status: response.status,
      kind: 'api',
    });
  }

  return new ApiClientError({
    message: `Request failed with status ${response.status}`,
    code: 'HTTP_ERROR',
    requestId: requestIdHeader,
    status: response.status,
    kind: 'parse',
  });
}

export interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: BodyInit | null;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  expect?: 'json' | 'blob' | 'text';
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<{ data: T; response: Response; requestId: string }> {
  const baseUrl = getApiBaseUrl();
  const requestId = createRequestId();
  const headers: Record<string, string> = {
    'X-Request-ID': requestId,
    ...(options.headers ?? {}),
  };

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method: options.method ?? 'GET',
      body: options.body ?? null,
      headers,
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    throw new ApiClientError({
      message:
        'Unable to reach the prediction API. Confirm the backend is running and VITE_API_BASE_URL is correct.',
      code: 'NETWORK_ERROR',
      requestId,
      kind: 'network',
    });
  }

  if (!response.ok) {
    throw await parseErrorResponse(response, requestId);
  }

  const expect = options.expect ?? 'json';
  if (expect === 'blob') {
    const data = (await response.blob()) as T;
    return {
      data,
      response,
      requestId: response.headers.get('X-Request-ID') ?? requestId,
    };
  }
  if (expect === 'text') {
    const data = (await response.text()) as T;
    return {
      data,
      response,
      requestId: response.headers.get('X-Request-ID') ?? requestId,
    };
  }

  try {
    const data = (await response.json()) as T;
    return {
      data,
      response,
      requestId: response.headers.get('X-Request-ID') ?? requestId,
    };
  } catch {
    throw new ApiClientError({
      message: 'The API returned an unreadable JSON response.',
      code: 'PARSE_ERROR',
      requestId: response.headers.get('X-Request-ID') ?? requestId,
      status: response.status,
      kind: 'parse',
    });
  }
}

export function buildUploadFormData(file: File, wellId?: string): FormData {
  const form = new FormData();
  form.append('file', file, file.name);
  const trimmed = wellId?.trim();
  if (trimmed) {
    form.append('well_id', trimmed);
  }
  return form;
}

export function parseContentDispositionFilename(
  header: string | null,
): string | null {
  if (!header) {
    return null;
  }
  const utfMatch = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (utfMatch?.[1]) {
    try {
      return decodeURIComponent(utfMatch[1].replace(/"/g, ''));
    } catch {
      return utfMatch[1].replace(/"/g, '');
    }
  }
  const plainMatch = /filename="?([^";]+)"?/i.exec(header);
  return plainMatch?.[1] ?? null;
}
