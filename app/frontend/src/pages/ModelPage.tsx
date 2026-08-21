import { ErrorAlert } from '../components/common/ErrorAlert';
import { MetricCard, StatusBadge } from '../components/common/StatusBadge';
import { useHealthQuery, useModelQuery } from '../hooks/useApiStatus';
import { formatDateTime, formatInteger, formatNumber } from '../utils/format';

type StageModel = {
  name: string;
  rmse: number;
  best?: boolean;
  weights?: string;
};

type TrainingStage = {
  title: string;
  metricNote: string;
  models: StageModel[];
  whyNext: string | null;
  current?: boolean;
};

const TRAINING_STAGES: TrainingStage[] = [
  {
    title: 'Baselines',
    metricNote: 'Mean RMSE across training wells',
    models: [
      { name: 'Last Known TVT', rmse: 12.81, best: true },
      { name: 'Linear Extrapolation', rmse: 58.14 },
      { name: 'Z→TVT Linear', rmse: 110.88 },
      { name: 'Formation Marker', rmse: 1017.93 },
    ],
    whyNext:
      'Simple rules gave a useful benchmark, but they cannot learn across wells or capture nonlinear geology and trajectory interactions.',
  },
  {
    title: 'Classic ML',
    metricNote: 'Out-of-fold RMSE (GroupKFold by well)',
    models: [
      { name: 'Random Forest', rmse: 105.0, best: true },
      { name: 'Linear Regression', rmse: 115.64 },
    ],
    whyNext:
      'Learning from features helped on harder wells, yet linear models were too rigid and Random Forest alone still left large errors.',
  },
  {
    title: 'Advanced models',
    metricNote: 'Out-of-fold RMSE after model comparison and tuning',
    models: [
      { name: 'Extra Trees (optimized)', rmse: 83.59, best: true },
      { name: 'XGBoost (optimized)', rmse: 93.43 },
      { name: 'LightGBM', rmse: 94.36 },
      { name: 'HistGradientBoosting', rmse: 95.6 },
    ],
    whyNext:
      'Boosting and Extra Trees improved accuracy after tuning, but the top models were close enough that combining them was worth testing.',
  },
  {
    title: 'Ensemble',
    metricNote: 'Out-of-fold RMSE for the best weighted blend',
    models: [
      {
        name: 'Weighted Extra Trees + XGBoost',
        rmse: 82.98,
        best: true,
        weights: 'Extra Trees 0.80 · XGBoost 0.20',
      },
    ],
    whyNext:
      'Direct TVT prediction still struggled on long prediction horizons, so residual learning plus a last-known blend was evaluated next.',
  },
  {
    title: 'Production blend',
    metricNote: 'Trailing-mask validation RMSE (production protocol)',
    models: [
      {
        name: 'Last-known + residual blend',
        rmse: 16.97,
        best: true,
        weights: 'Last-known TVT 0.70 · Residual projection 0.30',
      },
      {
        name: 'Residual ensemble (inside blend)',
        rmse: 19.42,
        weights: 'XGBoost 1.00 · Extra Trees 0.00',
      },
      { name: 'XGBoost residual alone', rmse: 19.42 },
      { name: 'Extra Trees residual alone', rmse: 21.66 },
      { name: 'Last Known TVT alone', rmse: 17.19 },
    ],
    whyNext: null,
    current: true,
  },
];

function formatWeight(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function ModelPage() {
  const modelQuery = useModelQuery();
  const healthQuery = useHealthQuery();

  const stages = TRAINING_STAGES.map((stage) => {
    if (!stage.current || !modelQuery.data) {
      return stage;
    }

    const alpha = modelQuery.data.alpha_last_known;
    const weightXgb = modelQuery.data.weight_xgboost;
    const weightEt = modelQuery.data.weight_extra_trees;
    const liveRmse = modelQuery.data.validation_rmse;

    return {
      ...stage,
      models: stage.models.map((model) => {
        if (model.name === 'Last-known + residual blend') {
          return {
            ...model,
            rmse: liveRmse ?? model.rmse,
            weights: `Last-known TVT ${formatWeight(alpha)} · Residual projection ${formatWeight(1 - alpha)}`,
          };
        }
        if (model.name === 'Residual ensemble (inside blend)') {
          return {
            ...model,
            weights: `XGBoost ${formatWeight(weightXgb)} · Extra Trees ${formatWeight(weightEt)}`,
          };
        }
        return model;
      }),
    };
  });

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

      <div className="stack">
        {modelQuery.data ? (
          <>
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
                {formatNumber(modelQuery.data.alpha_last_known, 2)} on
                last-known TVT and{' '}
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
                Validation wells are summarized by the training export
                artifacts when present on the model card.
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
          </>
        ) : null}

        <div className="card stack">
          <h2>Models trained</h2>
          <p className="help-text">
            How the modelling path progressed, with RMSE compared within each
            stage. Validation protocols differ between stages, so RMSE values
            are not directly comparable across stages.
          </p>
          <ol className="model-history">
            {stages.map((stage, index) => (
              <li
                key={stage.title}
                className={
                  stage.current
                    ? 'model-history-stage model-history-stage--current'
                    : 'model-history-stage'
                }
              >
                <div className="model-history-rail" aria-hidden="true">
                  <span className="model-history-step">{index + 1}</span>
                </div>
                <div className="model-history-body">
                  <div className="model-history-heading">
                    <h3 className="model-history-title">{stage.title}</h3>
                    {stage.current ? (
                      <span className="model-history-badge">In production</span>
                    ) : null}
                  </div>
                  <p className="model-history-metric-note">{stage.metricNote}</p>
                  <div className="model-rmse-table-wrap">
                    <table className="model-rmse-table">
                      <thead>
                        <tr>
                          <th scope="col">Model</th>
                          <th scope="col">RMSE</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stage.models.map((model) => (
                          <tr
                            key={model.name}
                            className={model.best ? 'is-best' : undefined}
                          >
                            <td>
                              <div className="model-rmse-name">
                                <span>{model.name}</span>
                                {model.best ? (
                                  <span className="model-rmse-best">Best</span>
                                ) : null}
                              </div>
                              {model.weights ? (
                                <div className="model-rmse-weights">
                                  Weights: {model.weights}
                                </div>
                              ) : null}
                            </td>
                            <td className="model-rmse-value">
                              {formatNumber(model.rmse, 2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {stage.whyNext ? (
                    <p className="model-history-why">
                      <span className="model-history-why-label">
                        Why we moved on
                      </span>
                      {stage.whyNext}
                    </p>
                  ) : (
                    <p className="model-history-why">
                      <span className="model-history-why-label">
                        Why this stayed
                      </span>
                      Residual correction plus last-known blending was the most
                      stable recipe for long missing TVT sections, so it became
                      the serving model.
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
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
    </>
  );
}
