import type { ModelInfoResponse } from '../types/api';
import { apiRequest } from './client';

export async function fetchCurrentModel(
  signal?: AbortSignal,
): Promise<ModelInfoResponse> {
  const { data } = await apiRequest<ModelInfoResponse>('/models/current', {
    signal,
  });
  return data;
}
