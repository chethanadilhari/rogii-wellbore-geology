import { useHealthQuery, useModelQuery } from '../../hooks/useApiStatus';
import { StatusBadge } from '../common/StatusBadge';

export function ModelStatus() {
  const healthQuery = useHealthQuery();
  const modelQuery = useModelQuery();

  if (healthQuery.isLoading) {
    return <StatusBadge label="Checking API…" tone="neutral" />;
  }

  if (healthQuery.isError || !healthQuery.data) {
    return <StatusBadge label="API Offline" tone="danger" />;
  }

  const version =
    healthQuery.data.model_version ??
    modelQuery.data?.model_version ??
    'unknown';

  return (
    <div className="row" style={{ gap: '0.5rem' }}>
      <StatusBadge label="API Online" tone="success" />
      <StatusBadge label={`Model ${version}`} tone="info" showDot={false} />
    </div>
  );
}
