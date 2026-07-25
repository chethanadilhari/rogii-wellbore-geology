import { useMemo, useState } from 'react';
import type { FullWellPredictionRow } from '../../types/well';
import { formatMissing, formatNumber } from '../../utils/format';

type SourceFilter = 'all' | 'known' | 'model';

interface PredictionTableProps {
  rows: FullWellPredictionRow[];
}

const PAGE_SIZE = 50;

export function PredictionTable({ rows }: PredictionTableProps) {
  const [filter, setFilter] = useState<SourceFilter>('all');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return rows.filter((row) => {
      const source = row.prediction_source.toLowerCase();
      if (filter !== 'all' && source !== filter) {
        return false;
      }
      if (!normalized) {
        return true;
      }
      return (
        String(row.original_row).includes(normalized) ||
        String(row.MD ?? '').toLowerCase().includes(normalized)
      );
    });
  }, [filter, query, rows]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = filtered.slice(
    safePage * PAGE_SIZE,
    safePage * PAGE_SIZE + PAGE_SIZE,
  );

  if (rows.length === 0) {
    return (
      <div className="empty-state" role="status">
        Result table is empty.
      </div>
    );
  }

  return (
    <div>
      <div className="toolbar">
        <label className="field" style={{ minWidth: '10rem' }}>
          <span className="sr-only">Filter by source</span>
          <select
            value={filter}
            onChange={(event) => {
              setFilter(event.target.value as SourceFilter);
              setPage(0);
            }}
            aria-label="Filter by prediction source"
          >
            <option value="all">All rows</option>
            <option value="known">Known only</option>
            <option value="model">Model only</option>
          </select>
        </label>
        <label className="field" style={{ flex: 1, minWidth: '12rem' }}>
          <span className="sr-only">Search by row or MD</span>
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(0);
            }}
            placeholder="Search by row or MD"
            aria-label="Search by row or MD"
          />
        </label>
        <span className="muted">
          Showing {pageRows.length} of {filtered.length} filtered rows
        </span>
      </div>

      <div className="table-wrap">
        <table className="data-table" aria-label="Prediction results">
          <thead>
            <tr>
              <th scope="col">Original row</th>
              <th scope="col">MD</th>
              <th scope="col">TVT_input</th>
              <th scope="col">Predicted TVT</th>
              <th scope="col">Prediction source</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row) => (
              <tr
                key={row.original_row}
                className={
                  row.prediction_source.toLowerCase() === 'model'
                    ? 'prediction-row'
                    : undefined
                }
              >
                <td>{row.original_row}</td>
                <td>{formatNumber(row.MD, 3)}</td>
                <td>{formatMissing(row.TVT_input)}</td>
                <td>{formatNumber(row.predicted_tvt, 4)}</td>
                <td>{row.prediction_source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pagination">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={safePage <= 0}
          onClick={() => setPage((current) => Math.max(0, current - 1))}
        >
          Previous
        </button>
        <span className="muted">
          Page {safePage + 1} of {pageCount}
        </span>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={safePage >= pageCount - 1}
          onClick={() =>
            setPage((current) => Math.min(pageCount - 1, current + 1))
          }
        >
          Next
        </button>
      </div>
    </div>
  );
}
