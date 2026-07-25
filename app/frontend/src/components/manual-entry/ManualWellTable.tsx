import { useMemo, useState } from 'react';
import type { ManualWellRow } from '../../types/well';
import { OPTIONAL_COLUMNS } from '../../types/well';
import {
  createEmptyManualRow,
  createExampleManualRows,
  findPredictionBoundary,
  getHistoryWarnings,
  isEmptyTvt,
  parseNumericCell,
  parsePastedTable,
} from '../../utils/manualWell';

interface ManualWellTableProps {
  wellId: string;
  onWellIdChange: (value: string) => void;
  rows: ManualWellRow[];
  onRowsChange: (rows: ManualWellRow[]) => void;
  disabled?: boolean;
}

export function ManualWellTable({
  wellId,
  onWellIdChange,
  rows,
  onRowsChange,
  disabled = false,
}: ManualWellTableProps) {
  const [showOptional, setShowOptional] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const boundary = useMemo(() => findPredictionBoundary(rows), [rows]);
  const warnings = useMemo(() => getHistoryWarnings(rows), [rows]);

  const updateCell = (
    rowId: string,
    key: keyof ManualWellRow,
    raw: string,
  ) => {
    onRowsChange(
      rows.map((row) => {
        if (row.id !== rowId) return row;
        if (key === 'id') return row;
        const parsed = parseNumericCell(raw);
        return {
          ...row,
          [key]: parsed === null ? row[key] : parsed,
        };
      }),
    );
  };

  const insertAt = (index: number) => {
    const next = [...rows];
    next.splice(index, 0, createEmptyManualRow());
    onRowsChange(next);
  };

  return (
    <div className="stack">
      <div className="alert alert-info" role="note">
        The model requires known TVT history before the prediction rows. Enter
        known measurements first, then add one or more rows with TVT_input left
        empty.
      </div>

      <div className="field" style={{ maxWidth: '22rem' }}>
        <label htmlFor="manual-well-id">Well ID</label>
        <input
          id="manual-well-id"
          value={wellId}
          disabled={disabled}
          onChange={(event) => onWellIdChange(event.target.value)}
          placeholder="manual_well"
        />
      </div>

      <div className="toolbar">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={disabled}
          onClick={() => onRowsChange([...rows, createEmptyManualRow()])}
        >
          Add row
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={disabled || rows.length === 0}
          onClick={() => onRowsChange([])}
        >
          Clear table
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={disabled}
          onClick={() => onRowsChange(createExampleManualRows())}
        >
          Load example
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setShowOptional((value) => !value)}
          aria-pressed={showOptional}
        >
          {showOptional ? 'Hide additional fields' : 'Additional fields'}
        </button>
      </div>

      {warnings.map((warning) => (
        <div key={warning} className="alert alert-warning" role="status">
          {warning}
        </div>
      ))}

      <div className="help-text">
        Known TVT rows
        <br />
        ──────────── prediction boundary ────────────
        <br />
        Rows requiring prediction
      </div>

      <div className="table-wrap">
        <table className="data-table" aria-label="Manual well entry table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">MD</th>
              <th scope="col">GR</th>
              <th scope="col">X</th>
              <th scope="col">Y</th>
              <th scope="col">Z</th>
              <th scope="col">TVT_input</th>
              {showOptional
                ? OPTIONAL_COLUMNS.map((column) => (
                    <th key={column} scope="col">
                      {column}
                    </th>
                  ))
                : null}
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={showOptional ? 14 : 8}>
                  Empty manual table. Add rows or load an example.
                </td>
              </tr>
            ) : (
              rows.map((row, index) => {
                const prediction = isEmptyTvt(row.TVT_input);
                const isBoundary =
                  boundary.firstPredictionIndex != null &&
                  index === boundary.firstPredictionIndex;
                return (
                  <tr
                    key={row.id}
                    className={[
                      prediction ? 'prediction-row' : '',
                      isBoundary ? 'boundary-row' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                  >
                    <td>{index + 1}</td>
                    {(
                      [
                        'MD',
                        'GR',
                        'X',
                        'Y',
                        'Z',
                        'TVT_input',
                      ] as const
                    ).map((column) => (
                      <td key={column}>
                        <input
                          aria-label={`${column} row ${index + 1}`}
                          inputMode="decimal"
                          disabled={disabled}
                          value={row[column] === null ? '' : String(row[column])}
                          onChange={(event) =>
                            updateCell(row.id, column, event.target.value)
                          }
                        />
                      </td>
                    ))}
                    {showOptional
                      ? OPTIONAL_COLUMNS.map((column) => (
                          <td key={column}>
                            <input
                              aria-label={`${column} row ${index + 1}`}
                              inputMode="decimal"
                              disabled={disabled}
                              value={
                                row[column] === null ? '' : String(row[column])
                              }
                              onChange={(event) =>
                                updateCell(row.id, column, event.target.value)
                              }
                            />
                          </td>
                        ))
                      : null}
                    <td>
                      <div className="row" style={{ gap: '0.35rem' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          disabled={disabled}
                          onClick={() => insertAt(index)}
                          aria-label={`Insert row before row ${index + 1}`}
                        >
                          Insert
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          disabled={disabled}
                          onClick={() =>
                            onRowsChange([
                              ...rows.slice(0, index + 1),
                              { ...row, id: crypto.randomUUID?.() ?? `${row.id}_copy` },
                              ...rows.slice(index + 1),
                            ])
                          }
                          aria-label={`Duplicate row ${index + 1}`}
                        >
                          Duplicate
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          disabled={disabled}
                          onClick={() =>
                            onRowsChange(rows.filter((item) => item.id !== row.id))
                          }
                          aria-label={`Remove row ${index + 1}`}
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Paste tabular data</h3>
        <p className="help-text">
          Paste CSV or tab-separated rows. A header row is optional.
        </p>
        <label className="field">
          <span className="sr-only">Paste tabular data</span>
          <textarea
            rows={4}
            value={pasteText}
            disabled={disabled}
            onChange={(event) => setPasteText(event.target.value)}
            placeholder="MD,GR,X,Y,Z,TVT_input"
          />
        </label>
        <div className="toolbar">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={disabled || !pasteText.trim()}
            onClick={() => {
              const parsed = parsePastedTable(pasteText);
              if (parsed.length > 0) {
                onRowsChange(parsed);
                setPasteText('');
              }
            }}
          >
            Apply pasted rows
          </button>
        </div>
      </div>
    </div>
  );
}
