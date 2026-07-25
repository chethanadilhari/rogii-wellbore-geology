import type { ReactNode } from 'react';

type BadgeTone = 'success' | 'warning' | 'danger' | 'neutral' | 'info';

interface StatusBadgeProps {
  label: string;
  tone?: BadgeTone;
  showDot?: boolean;
}

export function StatusBadge({
  label,
  tone = 'neutral',
  showDot = true,
}: StatusBadgeProps) {
  return (
    <span className={`badge badge-${tone}`}>
      {showDot ? <span className="status-dot" aria-hidden="true" /> : null}
      {label}
    </span>
  );
}

interface MetricCardProps {
  label: string;
  value: ReactNode;
  hint?: string;
}

export function MetricCard({ label, value, hint }: MetricCardProps) {
  return (
    <div className="card metric-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {hint ? <div className="hint">{hint}</div> : null}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state" role="status">
      <strong>{title}</strong>
      {description ? <p className="help-text">{description}</p> : null}
      {action ? <div style={{ marginTop: '0.75rem' }}>{action}</div> : null}
    </div>
  );
}

interface LoadingBannerProps {
  label: string;
}

export function LoadingBanner({ label }: LoadingBannerProps) {
  return (
    <div className="loading-banner" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
