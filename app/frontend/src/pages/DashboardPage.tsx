import { Link } from 'react-router-dom';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { MetricCard } from '../components/common/StatusBadge';
import { useHealthQuery, useModelQuery } from '../hooks/useApiStatus';
import { formatDateTime, formatInteger, formatNumber } from '../utils/format';

export function DashboardPage() {
  const healthQuery = useHealthQuery();
  const modelQuery = useModelQuery();

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>
          Predict missing TVT values for the trailing section of a horizontal
          well.
        </p>
      </div>

      {healthQuery.isError ? (
        <ErrorAlert
          error={healthQuery.error}
          title="API status unavailable"
          onRetry={() => {
            void healthQuery.refetch();
          }}
        />
      ) : null}

      {modelQuery.isError ? (
        <ErrorAlert
          error={modelQuery.error}
          title="Model metadata unavailable"
          onRetry={() => {
            void modelQuery.refetch();
          }}
        />
      ) : null}

      <div className="card-grid">
        <div className="span-8">
          <div className="card stack">
            <h2>Model summary</h2>
            {modelQuery.isLoading || healthQuery.isLoading ? (
              <p className="muted">Loading model and API status…</p>
            ) : (
              <div className="card-grid">
                <div className="span-4">
                  <MetricCard
                    label="Model version"
                    value={
                      modelQuery.data?.model_version ??
                      healthQuery.data?.model_version ??
                      '—'
                    }
                  />
                </div>
                <div className="span-4">
                  <MetricCard
                    label="Selected recipe"
                    value={
                      modelQuery.data?.selected_model ??
                      healthQuery.data?.selected_model ??
                      '—'
                    }
                  />
                </div>
                <div className="span-4">
                  <MetricCard
                    label="Validation RMSE"
                    value={formatNumber(modelQuery.data?.validation_rmse)}
                  />
                </div>
                <div className="span-4">
                  <MetricCard
                    label="Validation MAE"
                    value={formatNumber(modelQuery.data?.validation_mae)}
                  />
                </div>
                <div className="span-4">
                  <MetricCard
                    label="Feature count"
                    value={formatInteger(modelQuery.data?.feature_count)}
                  />
                </div>
                <div className="span-4">
                  <MetricCard
                    label="API status"
                    value={
                      healthQuery.data?.status === 'healthy'
                        ? 'Online'
                        : healthQuery.isError
                          ? 'Offline'
                          : 'Unknown'
                    }
                    hint={
                      modelQuery.data?.created_at_utc
                        ? `Created ${formatDateTime(modelQuery.data.created_at_utc)}`
                        : undefined
                    }
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="span-4">
          <div className="card stack">
            <h2>Workflow</h2>
            <ol className="workflow-list">
              <li>Provide well data</li>
              <li>Validate the well</li>
              <li>Generate predictions</li>
              <li>Review and download</li>
            </ol>
            <Link className="btn" to="/predict">
              Predict a Well
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
