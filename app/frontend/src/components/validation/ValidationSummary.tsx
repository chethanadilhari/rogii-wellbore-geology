import type { ValidateResponse, ValidationStatus } from '../../types/api';
import { formatInteger } from '../../utils/format';
import { StatusBadge } from '../common/StatusBadge';

interface ValidationSummaryProps {
  result: ValidateResponse | null;
  status: ValidationStatus | null;
  clientWarnings?: string[];
}

function resolveTone(status: ValidationStatus | null) {
  if (status === 'valid') return 'success' as const;
  if (status === 'warning') return 'warning' as const;
  if (status === 'invalid') return 'danger' as const;
  return 'neutral' as const;
}

export function ValidationSummary({
  result,
  status,
  clientWarnings = [],
}: ValidationSummaryProps) {
  if (!result || !status) {
    return (
      <div className="empty-state" role="status">
        Validate the well to see a backend summary.
      </div>
    );
  }

  const warnings = [...clientWarnings, ...(result.warnings ?? [])];

  return (
    <div className="stack">
      <div className="row">
        <StatusBadge
          label={status === 'valid' ? 'Valid' : status === 'warning' ? 'Warning' : 'Invalid'}
          tone={resolveTone(status)}
        />
        <span className="muted">Well ID: {result.well_id}</span>
      </div>

      <div className="card-grid">
        <div className="span-3">
          <div className="card metric-card">
            <div className="label">Total rows</div>
            <div className="value">{formatInteger(result.total_rows)}</div>
          </div>
        </div>
        <div className="span-3">
          <div className="card metric-card">
            <div className="label">Known rows</div>
            <div className="value">{formatInteger(result.known_rows)}</div>
          </div>
        </div>
        <div className="span-3">
          <div className="card metric-card">
            <div className="label">Prediction rows</div>
            <div className="value">{formatInteger(result.prediction_rows)}</div>
          </div>
        </div>
        <div className="span-3">
          <div className="card metric-card">
            <div className="label">Rows reordered</div>
            <div className="value">
              {result.rows_reordered_for_processing ? 'Yes' : 'No'}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Prediction interval</h3>
        <p className="help-text">
          First prediction row:{' '}
          <strong>
            {result.first_prediction_original_index == null
              ? '—'
              : result.first_prediction_original_index}
          </strong>
          {' · '}
          Last prediction row:{' '}
          <strong>
            {result.last_prediction_original_index == null
              ? '—'
              : result.last_prediction_original_index}
          </strong>
        </p>
      </div>

      {warnings.length > 0 ? (
        <div className="alert alert-warning" role="status">
          <div className="alert-title">Warnings</div>
          <ul className="list-plain">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
