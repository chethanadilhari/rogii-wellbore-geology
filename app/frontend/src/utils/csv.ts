import type {
  ChartSeriesPoint,
  FullWellPredictionRow,
} from '../types/well';

function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === ',' && !inQuotes) {
      cells.push(current);
      current = '';
      continue;
    }
    current += char;
  }
  cells.push(current);
  return cells;
}

function parseNullableNumber(value: string | undefined): number | null {
  if (value == null) {
    return null;
  }
  const trimmed = value.trim();
  if (trimmed === '' || trimmed.toLowerCase() === 'nan') {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export function parseCsvRecords(text: string): Record<string, string>[] {
  const normalized = text.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = normalized.split('\n').filter((line) => line.trim().length > 0);
  if (lines.length === 0) {
    return [];
  }

  const headers = splitCsvLine(lines[0]).map((header) => header.trim());
  return lines.slice(1).map((line) => {
    const cells = splitCsvLine(line);
    const record: Record<string, string> = {};
    headers.forEach((header, index) => {
      record[header] = cells[index] ?? '';
    });
    return record;
  });
}

export function parseFullWellPredictions(
  text: string,
): FullWellPredictionRow[] {
  const records = parseCsvRecords(text);
  return records.map((record, index) => ({
    original_row: index,
    MD: parseNullableNumber(record.MD),
    TVT_input: parseNullableNumber(record.TVT_input),
    predicted_tvt: parseNullableNumber(record.predicted_tvt),
    prediction_source: (record.prediction_source || '').trim() || 'unknown',
  }));
}

export function toChartSeries(
  rows: FullWellPredictionRow[],
): ChartSeriesPoint[] {
  return rows
    .filter((row) => row.MD != null && Number.isFinite(row.MD))
    .map((row) => {
      const source = row.prediction_source.toLowerCase();
      const isKnown = source === 'known';
      return {
        MD: row.MD as number,
        knownTvt: isKnown ? row.TVT_input ?? row.predicted_tvt : null,
        predictedTvt: !isKnown ? row.predicted_tvt : null,
        predictionSource: row.prediction_source,
      };
    });
}

export function countCsvDataRows(text: string): number {
  return parseCsvRecords(text).length;
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
