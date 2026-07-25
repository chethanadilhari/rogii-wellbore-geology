import { ApiClientError } from '../api/client';

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred.';
}

export function getErrorCode(error: unknown): string | null {
  if (error instanceof ApiClientError) {
    return error.code;
  }
  return null;
}

export function getErrorRequestId(error: unknown): string | null {
  if (error instanceof ApiClientError && error.requestId) {
    return error.requestId;
  }
  return null;
}

export function getErrorDetails(
  error: unknown,
): Record<string, unknown> | null {
  if (error instanceof ApiClientError) {
    return error.details;
  }
  return null;
}
