import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PredictPage } from '../pages/PredictPage';

function renderPredict() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PredictPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PredictPage workflow', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('keeps predict disabled until validation succeeds and then requests both outputs', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/validate')) {
        return new Response(
          JSON.stringify({
            valid: true,
            well_id: 'demo',
            total_rows: 3,
            known_rows: 2,
            prediction_rows: 1,
            first_prediction_original_index: 2,
            last_prediction_original_index: 2,
            rows_reordered_for_processing: false,
            warnings: [],
            errors: [],
          }),
          { status: 200 },
        );
      }
      if (url.endsWith('/predict')) {
        return new Response('id,tvt\ndemo_2,101\n', {
          status: 200,
          headers: {
            'Content-Disposition': 'attachment; filename="demo_submission.csv"',
            'X-Model-Version': 'v_test',
            'X-Selected-Model': 'blend_lastknown_0.70_ensemble',
            'X-Well-Id': 'demo',
            'X-Total-Rows': '3',
            'X-Known-Rows': '2',
            'X-Prediction-Rows': '1',
          },
        });
      }
      if (url.endsWith('/predict/full-well')) {
        return new Response(
          [
            'MD,GR,X,Y,Z,TVT_input,predicted_tvt,prediction_source',
            '1,1,1,1,1,100,100,known',
            '2,1,1,1,1,101,101,known',
            '3,1,1,1,1,,102,model',
          ].join('\n'),
          {
            status: 200,
            headers: {
              'Content-Disposition':
                'attachment; filename="demo_full_well_predictions.csv"',
              'X-Model-Version': 'v_test',
              'X-Selected-Model': 'blend_lastknown_0.70_ensemble',
              'X-Well-Id': 'demo',
              'X-Total-Rows': '3',
              'X-Known-Rows': '2',
              'X-Prediction-Rows': '1',
            },
          },
        );
      }
      return new Response('{}', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    renderPredict();

    expect(
      screen.getByRole('button', { name: /generate prediction/i }),
    ).toBeDisabled();

    await user.click(screen.getByRole('tab', { name: /manual well entry/i }));
    await user.click(screen.getByRole('button', { name: /load example/i }));
    await user.click(screen.getByRole('button', { name: /validate well/i }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /generate prediction/i }),
      ).toBeEnabled();
    });
    expect(screen.getByText('Warning')).toBeInTheDocument();

    await user.click(
      screen.getByRole('button', { name: /generate prediction/i }),
    );

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /download competition csv/i }),
      ).toBeInTheDocument();
    });

    const calledUrls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(calledUrls.some((url) => url.endsWith('/validate'))).toBe(true);
    expect(calledUrls.some((url) => url.endsWith('/predict'))).toBe(true);
    expect(calledUrls.some((url) => url.endsWith('/predict/full-well'))).toBe(
      true,
    );
    expect(screen.getByRole('heading', { name: 'Prediction boundary' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /prediction results/i })).toBeInTheDocument();
  });

  it('displays structured validation errors and keeps predict disabled', async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'NON_TRAILING_TVT_GAP',
              message: 'Missing TVT is not a clean trailing interval.',
              details: {},
              request_id: 'req-err',
            },
          }),
          { status: 422 },
        ),
      ),
    );

    renderPredict();
    await user.click(screen.getByRole('tab', { name: /manual well entry/i }));
    await user.click(screen.getByRole('button', { name: /load example/i }));
    await user.click(screen.getByRole('button', { name: /validate well/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        /clean trailing interval/i,
      );
    });
    expect(screen.getByText(/NON_TRAILING_TVT_GAP/)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /generate prediction/i }),
    ).toBeDisabled();
  });

  it('resets validated state after editing the manual table', async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            valid: true,
            well_id: 'manual_well',
            total_rows: 16,
            known_rows: 12,
            prediction_rows: 4,
            first_prediction_original_index: 12,
            last_prediction_original_index: 15,
            rows_reordered_for_processing: false,
            warnings: [],
            errors: [],
          }),
          { status: 200 },
        ),
      ),
    );

    renderPredict();
    await user.click(screen.getByRole('tab', { name: /manual well entry/i }));
    await user.click(screen.getByRole('button', { name: /load example/i }));
    await user.click(screen.getByRole('button', { name: /validate well/i }));
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /generate prediction/i }),
      ).toBeEnabled();
    });

    await user.type(screen.getByLabelText('MD row 1'), '9');
    expect(
      screen.getByRole('button', { name: /generate prediction/i }),
    ).toBeDisabled();
  });

  it('supports keyboard-operable input mode tabs', async () => {
    const user = userEvent.setup();
    renderPredict();
    const tabs = screen.getByRole('tablist', { name: /input mode/i });
    expect(within(tabs).getByRole('tab', { name: /upload csv/i })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    await user.click(within(tabs).getByRole('tab', { name: /manual well entry/i }));
    expect(
      within(tabs).getByRole('tab', { name: /manual well entry/i }),
    ).toHaveAttribute('aria-selected', 'true');
  });
});
