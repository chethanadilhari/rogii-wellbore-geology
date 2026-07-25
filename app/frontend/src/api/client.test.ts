import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiClientError,
  apiRequest,
  buildUploadFormData,
  getApiBaseUrl,
  parseContentDispositionFilename,
} from '../api/client';
import { fetchHealth } from '../api/health';
import { fetchCurrentModel } from '../api/models';
import { validateWell } from '../api/validation';
import { predictCompetition } from '../api/prediction';

describe('API client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('reads VITE_API_BASE_URL', () => {
    expect(getApiBaseUrl()).toMatch(/127\.0\.0\.1:8000|localhost:8000/);
  });

  it('parses health responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: 'healthy',
            model_loaded: true,
            model_version: 'v_test',
            selected_model: 'blend_lastknown_0.70_ensemble',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );

    await expect(fetchHealth()).resolves.toMatchObject({
      status: 'healthy',
      model_loaded: true,
      model_version: 'v_test',
    });
  });

  it('parses model responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            model_version: 'v_test',
            selected_model: 'blend_lastknown_0.70_ensemble',
            validation_rmse: 1.2,
            validation_mae: 0.8,
            feature_count: 4,
            required_predictors: ['last_known', 'xgboost_residual'],
            optional_predictors: ['extra_trees_residual'],
            alpha_last_known: 0.7,
            weight_extra_trees: 0,
            weight_xgboost: 1,
            training_wells: 10,
            final_fit_rows: 1000,
            created_at_utc: '2026-01-01T00:00:00Z',
          }),
          { status: 200 },
        ),
      ),
    );

    await expect(fetchCurrentModel()).resolves.toMatchObject({
      model_version: 'v_test',
      feature_count: 4,
      alpha_last_known: 0.7,
    });
  });

  it('parses structured API errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'NON_TRAILING_TVT_GAP',
              message: 'Missing TVT is not a clean trailing interval.',
              details: { well_id: 'abc' },
              request_id: 'req-123',
            },
          }),
          {
            status: 422,
            headers: { 'X-Request-ID': 'req-123' },
          },
        ),
      ),
    );

    await expect(apiRequest('/validate', { method: 'POST' })).rejects.toEqual(
      expect.objectContaining({
        name: 'ApiClientError',
        code: 'NON_TRAILING_TVT_GAP',
        requestId: 'req-123',
        status: 422,
      }),
    );
  });

  it('handles network failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    );

    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiClientError);
    await expect(fetchHealth()).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
      kind: 'network',
    });
  });

  it('supports CSV blob downloads', async () => {
    const csv = 'id,tvt\nwell_1,100\n';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(csv, {
          status: 200,
          headers: {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename="well_submission.csv"',
            'X-Model-Version': 'v_test',
            'X-Well-Id': 'well',
            'X-Prediction-Rows': '1',
          },
        }),
      ),
    );

    const file = new File(['MD,GR,X,Y,Z,TVT_input\n1,1,1,1,1,\n'], 'well.csv', {
      type: 'text/csv',
    });
    const result = await predictCompetition(file, 'well');
    expect(result.filename).toBe('well_submission.csv');
    expect(result.text).toContain('id,tvt');
    expect(result.headers.predictionRows).toBe(1);
  });

  it('builds multipart form data and validates successfully', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            valid: true,
            well_id: 'abc',
            total_rows: 10,
            known_rows: 6,
            prediction_rows: 4,
            first_prediction_original_index: 6,
            last_prediction_original_index: 9,
            rows_reordered_for_processing: false,
            warnings: [],
            errors: [],
          }),
          { status: 200 },
        ),
      ),
    );

    const file = new File(['MD,GR,X,Y,Z,TVT_input\n'], 'abc.csv', {
      type: 'text/csv',
    });
    const form = buildUploadFormData(file, 'abc');
    expect(form.get('well_id')).toBe('abc');
    await expect(validateWell(file, 'abc')).resolves.toMatchObject({
      valid: true,
      well_id: 'abc',
      prediction_rows: 4,
    });
  });

  it('parses Content-Disposition filenames', () => {
    expect(
      parseContentDispositionFilename(
        'attachment; filename="000d7d20_submission.csv"',
      ),
    ).toBe('000d7d20_submission.csv');
  });
});
