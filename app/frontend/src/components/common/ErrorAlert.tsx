import { useState } from 'react';
import {
  getErrorCode,
  getErrorDetails,
  getErrorMessage,
  getErrorRequestId,
} from '../../utils/errors';

interface ErrorAlertProps {
  error: unknown;
  title?: string;
  onRetry?: () => void;
}

export function ErrorAlert({
  error,
  title = 'Request failed',
  onRetry,
}: ErrorAlertProps) {
  const [open, setOpen] = useState(false);
  const message = getErrorMessage(error);
  const code = getErrorCode(error);
  const requestId = getErrorRequestId(error);
  const details = getErrorDetails(error);

  return (
    <div className="alert alert-error" role="alert">
      <div className="alert-title">{title}</div>
      <p>{message}</p>
      {code ? (
        <p className="help-text">
          Error code: <span className="mono">{code}</span>
        </p>
      ) : null}
      {(requestId || details) && (
        <details
          open={open}
          onToggle={(event) =>
            setOpen((event.target as HTMLDetailsElement).open)
          }
        >
          <summary>Technical details</summary>
          <div className="stack" style={{ marginTop: '0.5rem' }}>
            {requestId ? (
              <p className="help-text">
                Request ID: <span className="mono">{requestId}</span>
              </p>
            ) : null}
            {details && Object.keys(details).length > 0 ? (
              <pre className="mono" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                {JSON.stringify(details, null, 2)}
              </pre>
            ) : null}
          </div>
        </details>
      )}
      {onRetry ? (
        <div style={{ marginTop: '0.75rem' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry}>
            Retry
          </button>
        </div>
      ) : null}
    </div>
  );
}
