import type { PredictionResult, ValidateResponse } from '../../types/api';
import type { FullWellPredictionRow } from '../../types/well';
import { downloadBlob } from '../../utils/csv';
import { formatInteger } from '../../utils/format';
import { MetricCard } from '../common/StatusBadge';
import { PredictionChart } from '../charts/PredictionChart';
import { PredictionTable } from '../tables/PredictionTable';
import type { ChartSeriesPoint } from '../../types/well';

interface DownloadPanelProps {
  competition: PredictionResult | null;
  fullWell: PredictionResult | null;
  disabled?: boolean;
}

export function DownloadPanel({
  competition,
  fullWell,
  disabled = false,
}: DownloadPanelProps) {
  if (!competition && !fullWell) {
    return (
      <div className="empty-state" role="status">
        Downloads become available after prediction completes.
      </div>
    );
  }

  return (
    <div className="row">
      <button
        type="button"
        className="btn"
        disabled={disabled || !competition}
        onClick={() => {
          if (!competition) return;
          downloadBlob(competition.blob, competition.filename);
        }}
      >
        Download Competition CSV
      </button>
      <button
        type="button"
        className="btn btn-secondary"
        disabled={disabled || !fullWell}
        onClick={() => {
          if (!fullWell) return;
          downloadBlob(fullWell.blob, fullWell.filename);
        }}
      >
        Download Full Well CSV
      </button>
      {!competition || !fullWell ? (
        <span className="muted">One or more downloads are unavailable.</span>
      ) : null}
    </div>
  );
}

interface PredictionBoundaryCardProps {
  rows: FullWellPredictionRow[];
}

export function PredictionBoundaryCard({ rows }: PredictionBoundaryCardProps) {
  const lastKnown = [...rows]
    .reverse()
    .find((row) => row.prediction_source.toLowerCase() === 'known');
  const modelRows = rows.filter(
    (row) => row.prediction_source.toLowerCase() === 'model',
  );
  const firstModel = modelRows[0];
  const lastModel = modelRows[modelRows.length - 1];

  return (
    <div className="card">
      <h3>Prediction boundary</h3>
      <ul className="list-plain">
        <li>
          Last known TVT row:{' '}
          <strong>
            {lastKnown
              ? `${lastKnown.original_row} (MD ${lastKnown.MD ?? '—'})`
              : '—'}
          </strong>
        </li>
        <li>
          First model-predicted row:{' '}
          <strong>
            {firstModel
              ? `${firstModel.original_row} (MD ${firstModel.MD ?? '—'})`
              : '—'}
          </strong>
        </li>
        <li>
          Last predicted row:{' '}
          <strong>
            {lastModel
              ? `${lastModel.original_row} (MD ${lastModel.MD ?? '—'})`
              : '—'}
          </strong>
        </li>
      </ul>
    </div>
  );
}

interface PredictionResultsProps {
  validation: ValidateResponse;
  competition: PredictionResult;
  fullWell: PredictionResult;
  rows: FullWellPredictionRow[];
  chartData: ChartSeriesPoint[];
}

export function PredictionResults({
  validation,
  competition,
  fullWell,
  rows,
  chartData,
}: PredictionResultsProps) {
  const headers = fullWell.headers;
  return (
    <div className="stack">
      <div className="card-grid">
        <div className="span-4">
          <MetricCard
            label="Well ID"
            value={headers.wellId ?? validation.well_id}
          />
        </div>
        <div className="span-4">
          <MetricCard
            label="Total rows"
            value={formatInteger(headers.totalRows ?? validation.total_rows)}
          />
        </div>
        <div className="span-4">
          <MetricCard
            label="Known rows"
            value={formatInteger(headers.knownRows ?? validation.known_rows)}
          />
        </div>
        <div className="span-4">
          <MetricCard
            label="Predicted rows"
            value={formatInteger(
              headers.predictionRows ?? validation.prediction_rows,
            )}
          />
        </div>
        <div className="span-4">
          <MetricCard
            label="Model version"
            value={headers.modelVersion ?? '—'}
          />
        </div>
        <div className="span-4">
          <MetricCard
            label="Selected model"
            value={headers.selectedModel ?? '—'}
          />
        </div>
      </div>

      <div className="card">
        <h3>TVT versus MD</h3>
        <PredictionChart data={chartData} />
      </div>

      <PredictionBoundaryCard rows={rows} />

      <div className="card">
        <h3>Prediction result table</h3>
        <PredictionTable rows={rows} />
      </div>

      <div className="card">
        <h3>Download</h3>
        <DownloadPanel competition={competition} fullWell={fullWell} />
        <p className="help-text" style={{ marginTop: '0.65rem' }}>
          Files are the exact backend responses ({competition.filename},{' '}
          {fullWell.filename}). Competition CSV contains prediction rows only.
        </p>
      </div>
    </div>
  );
}
