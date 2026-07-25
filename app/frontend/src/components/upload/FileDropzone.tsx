import { useCallback, useId, useRef, useState } from 'react';
import { formatBytes } from '../../utils/format';

interface FileDropzoneProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  accept?: string;
  disabled?: boolean;
}

export function FileDropzone({
  file,
  onFileChange,
  accept = '.csv,text/csv',
  disabled = false,
}: FileDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [active, setActive] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const applyFile = useCallback(
    (next: File | null) => {
      setLocalError(null);
      if (!next) {
        onFileChange(null);
        return;
      }
      if (!next.name.toLowerCase().endsWith('.csv')) {
        setLocalError('Only .csv files are accepted.');
        onFileChange(null);
        return;
      }
      if (next.size === 0) {
        setLocalError('The selected file is empty.');
        onFileChange(null);
        return;
      }
      onFileChange(next);
    },
    [onFileChange],
  );

  return (
    <div>
      <div
        className={`dropzone${active ? ' active' : ''}`}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!disabled) setActive(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setActive(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setActive(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setActive(false);
          if (disabled) return;
          const dropped = event.dataTransfer.files?.[0] ?? null;
          applyFile(dropped);
        }}
      >
        <p>
          <strong>Drag and drop a horizontal-well CSV</strong>
        </p>
        <p className="help-text">
          Required columns: MD, GR, X, Y, Z, TVT_input. Optional markers:
          ANCC, ASTNU, ASTNL, EGFDU, EGFDL, BUDA, TVT.
        </p>
        <p className="help-text">
          TVT_input must contain known values first, followed by one trailing
          missing interval.
        </p>
        <div className="dropzone-actions">
          <label className="btn btn-secondary" htmlFor={inputId}>
            Browse CSV
          </label>
          <input
            id={inputId}
            ref={inputRef}
            className="sr-only"
            type="file"
            accept={accept}
            disabled={disabled}
            onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              applyFile(selected);
              event.target.value = '';
            }}
          />
        </div>
      </div>

      {localError ? (
        <p className="alert alert-error" role="alert" style={{ marginTop: '0.75rem' }}>
          {localError}
        </p>
      ) : null}

      {file ? (
        <div className="file-meta">
          <StatusFileMeta file={file} />
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              applyFile(null);
              if (inputRef.current) inputRef.current.value = '';
            }}
          >
            Remove file
          </button>
        </div>
      ) : (
        <p className="help-text" style={{ marginTop: '0.75rem' }}>
          No file selected.
        </p>
      )}
    </div>
  );
}

function StatusFileMeta({ file }: { file: File }) {
  return (
    <>
      <span>
        <strong>{file.name}</strong>
      </span>
      <span className="muted">{formatBytes(file.size)}</span>
    </>
  );
}
