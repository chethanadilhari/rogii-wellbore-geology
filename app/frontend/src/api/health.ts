import type { HealthResponse } from '../types/api';
import { apiRequest } from './client';

export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const { data } = await apiRequest<HealthResponse>('/health', { signal });
  return data;
}
