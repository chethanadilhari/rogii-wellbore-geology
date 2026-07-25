import { ErrorAlert } from '../components/common/ErrorAlert';
import { MetricCard, StatusBadge } from '../components/common/StatusBadge';
import { useHealthQuery, useModelQuery } from '../hooks/useApiStatus';
import { formatDateTime, formatInteger, formatNumber } from '../utils/format';

export function ModelPage() {
  const modelQuery = useModelQuery();
  const healthQuery = useHealthQuery();

  return (
    <>
      <div className="page-header">
        <h1>Model Information</h1>
        <p>
          Production residual-blend recipe used to predict missing TVT values in
          the trailing section of a horizontal well.
        </p>
      </div>

      {modelQuery.isLoading ? (
        <p className="muted" role="status">
          Loading model metadata…
        </p>
      ) : null}

      {modelQuery.isError ? (
        <ErrorAlert
          error={modelQuery.error}
          title="Unable to load model information"
          onRetry={() => {
            void modelQuery.refetch();
          }}
        />
      ) : null}

      {modelQuery.data ? (
        <div className="stack">
          <div className="card">
            <h2>Production model</h2>
            <div className="card-grid">
              <div className="span-3">
                <MetricCard
                  label="Model version"
                  value={modelQuery.data.model_version}
                />
              </div>
              <div className="span-3">
                <MetricCard
                  label="Selected recipe"
                  value={modelQuery.data.selected_model}
                />
              </div>
              <div className="span-3">
                <MetricCard
                  label="Created date"
                  value={formatDateTime(modelQuery.data.created_at_utc)}
                />
              </div>
              <div className="span-3">
                <MetricCard
                  label="Feature count"
                  value={formatInteger(modelQuery.data.feature_count)}
                />
              </div>
            </div>
          </div>

          <div className="card stack">
            <h2>Prediction formula</h2>
            <div className="formula-block">
{`Final TVT =
70% Last Known TVT
+
30% Residual-Corrected Projection`}
            </div>
            <p className="help-text">
              Residual-Corrected Projection = Linear TVT Projection + XGBoost
              Residual Prediction
            </p>
            <p className="help-text">
              Current blend uses α ={' '}
              {formatNumber(modelQuery.data.alpha_last_known, 2)} on last-known
              TVT and{' '}
              {formatNumber(1 - modelQuery.data.alpha_last_known, 2)} on the
              residual-corrected projection.
            </p>
            <details>
              <summary>Technical details</summary>
              <pre className="mono" style={{ whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(
                  {
                    alpha_last_known: modelQuery.data.alpha_last_known,
                    weight_xgboost: modelQuery.data.weight_xgboost,
                    weight_extra_trees: modelQuery.data.weight_extra_trees,
                    required_predictors: modelQuery.data.required_predictors,
                    optional_predictors: modelQuery.data.optional_predictors,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          </div>

          <div className="card">
            <h2>Validation metrics</h2>
            <div className="card-grid">
              <div className="span-3">
                <MetricCard
                  label="RMSE"
                  value={formatNumber(modelQuery.data.validation_rmse)}
                />
              </div>
              <div className="span-3">
                <MetricCard
                  label="MAE"
                  value={formatNumber(modelQuery.data.validation_mae)}
                />
              </div>
              <div className="span-3">
                <MetricCard
                  label="Training wells"
                  value={formatInteger(modelQuery.data.training_wells)}
                />
              </div>
              <div className="span-3">
                <MetricCard
                  label="Final fit rows"
                  value={formatInteger(modelQuery.data.final_fit_rows)}
                />
              </div>
            </div>
            <p className="help-text" style={{ marginTop: '0.75rem' }}>
              Validation wells are summarized by the training export artifacts
              when present on the model card.
            </p>
          </div>

          <div className="card stack">
            <h2>Predictors</h2>
            <ul className="list-plain">
              <li>Last-known TVT</li>
              <li>XGBoost residual model</li>
              <li>
                Extra Trees weight:{' '}
                {formatNumber(modelQuery.data.weight_extra_trees, 2)}
                {modelQuery.data.weight_extra_trees === 0
                  ? ' — Not loaded by the production pipeline'
                  : ''}
              </li>
            </ul>
          </div>

          <div className="card stack">
            <h2>Artifact status</h2>
            <div className="row">
              <StatusBadge
                label={
                  healthQuery.data?.model_loaded
                    ? 'Model loaded'
                    : 'Model unavailable'
                }
                tone={healthQuery.data?.model_loaded ? 'success' : 'danger'}
              />
              <StatusBadge
                label="Checksum verification enabled"
                tone="info"
                showDot={false}
              />
              <StatusBadge
                label={
                  healthQuery.data?.status === 'healthy'
                    ? 'API healthy'
                    : 'API offline'
                }
                tone={
                  healthQuery.data?.status === 'healthy' ? 'success' : 'danger'
                }
              />
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
