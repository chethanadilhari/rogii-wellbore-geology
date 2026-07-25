import type { ValidateResponse } from '../types/api';
import { apiRequest, buildUploadFormData } from './client';

export async function validateWell(
  file: File,
  wellId?: string,
  signal?: AbortSignal,
): Promise<ValidateResponse> {
  const { data } = await apiRequest<ValidateResponse>('/validate', {
    method: 'POST',
    body: buildUploadFormData(file, wellId),
    signal,
  });
  return data;
}
