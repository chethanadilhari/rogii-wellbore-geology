import type { PredictionHeaders, PredictionResult } from '../types/api';
import {
  apiRequest,
  buildUploadFormData,
  parseContentDispositionFilename,
} from './client';

function parseOptionalInt(value: string | null): number | null {
  if (value == null || value === '') {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function extractPredictionHeaders(response: Response): PredictionHeaders {
  return {
    modelVersion: response.headers.get('X-Model-Version'),
    selectedModel: response.headers.get('X-Selected-Model'),
    wellId: response.headers.get('X-Well-Id'),
    totalRows: parseOptionalInt(response.headers.get('X-Total-Rows')),
    knownRows: parseOptionalInt(response.headers.get('X-Known-Rows')),
    predictionRows: parseOptionalInt(response.headers.get('X-Prediction-Rows')),
    requestId: response.headers.get('X-Request-ID'),
    filename: parseContentDispositionFilename(
      response.headers.get('Content-Disposition'),
    ),
  };
}

async function predictCsv(
  path: string,
  file: File,
  wellId: string | undefined,
  fallbackFilename: string,
  signal?: AbortSignal,
): Promise<PredictionResult> {
  const { data, response } = await apiRequest<Blob>(path, {
    method: 'POST',
    body: buildUploadFormData(file, wellId),
    expect: 'blob',
    signal,
  });
  const headers = extractPredictionHeaders(response);
  const text = await data.text();
  return {
    blob: new Blob([text], { type: 'text/csv;charset=utf-8' }),
    text,
    headers,
    filename: headers.filename ?? fallbackFilename,
  };
}

export async function predictCompetition(
  file: File,
  wellId?: string,
  signal?: AbortSignal,
): Promise<PredictionResult> {
  const safeId = wellId?.trim() || 'well';
  return predictCsv(
    '/predict',
    file,
    wellId,
    `${safeId}_submission.csv`,
    signal,
  );
}

export async function predictFullWell(
  file: File,
  wellId?: string,
  signal?: AbortSignal,
): Promise<PredictionResult> {
  const safeId = wellId?.trim() || 'well';
  return predictCsv(
    '/predict/full-well',
    file,
    wellId,
    `${safeId}_full_well_predictions.csv`,
    signal,
  );
}
