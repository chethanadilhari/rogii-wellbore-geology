import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ModelPage } from '../pages/ModelPage';

function renderModel() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <ModelPage />
    </QueryClientProvider>,
  );
}

describe('ModelPage', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('displays model metadata and recipe', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/models/current')) {
          return new Response(
            JSON.stringify({
              model_version: 'v_test',
              selected_model: 'blend_lastknown_0.70_ensemble',
              validation_rmse: 16.9,
              validation_mae: 12.1,
              feature_count: 4,
              required_predictors: ['last_known', 'xgboost_residual'],
              optional_predictors: ['extra_trees_residual'],
              alpha_last_known: 0.7,
              weight_extra_trees: 0,
              weight_xgboost: 1,
              training_wells: 42,
              final_fit_rows: 10000,
              created_at_utc: '2026-01-01T00:00:00Z',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response(
          JSON.stringify({
            status: 'healthy',
            model_loaded: true,
            model_version: 'v_test',
            selected_model: 'blend_lastknown_0.70_ensemble',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }),
    );

    renderModel();

    await waitFor(() => {
      expect(screen.getByText('v_test')).toBeInTheDocument();
    });
    expect(screen.getByText('blend_lastknown_0.70_ensemble')).toBeInTheDocument();
    expect(screen.getByText(/70% Last Known TVT/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Not loaded by the production pipeline/i),
    ).toBeInTheDocument();
  });

  it('shows an API error state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: {
              code: 'MODEL_UNAVAILABLE',
              message: 'Model is unavailable.',
              details: {},
              request_id: 'req-model',
            },
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      ),
    );

    renderModel();
    expect(
      await screen.findByRole('alert', {}, { timeout: 3000 }),
    ).toHaveTextContent(/unavailable/i);
  });
});
