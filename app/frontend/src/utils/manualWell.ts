import {
  OPTIONAL_COLUMNS,
  REQUIRED_COLUMNS,
  type ManualWellRow,
  type OptionalColumn,
} from '../types/well';

function createRowId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `row_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function createEmptyManualRow(
  overrides: Partial<ManualWellRow> = {},
): ManualWellRow {
  return {
    id: createRowId(),
    MD: '',
    GR: '',
    X: '',
    Y: '',
    Z: '',
    TVT_input: '',
    ANCC: '',
    ASTNU: '',
    ASTNL: '',
    EGFDU: '',
    EGFDL: '',
    BUDA: '',
    ...overrides,
  };
}

export function isEmptyTvt(value: ManualWellRow['TVT_input']): boolean {
  return value === '' || value === null;
}

export function countKnownTvtRows(rows: ManualWellRow[]): number {
  return rows.filter((row) => !isEmptyTvt(row.TVT_input)).length;
}

export function countPredictionRows(rows: ManualWellRow[]): number {
  return rows.filter((row) => isEmptyTvt(row.TVT_input)).length;
}

export function getHistoryWarnings(rows: ManualWellRow[]): string[] {
  const known = countKnownTvtRows(rows);
  const warnings: string[] = [];
  if (known > 0 && known < 10) {
    warnings.push(
      'Fewer than 10 known TVT rows were provided. Prediction reliability may be poor.',
    );
  } else if (known > 0 && known < 50) {
    warnings.push(
      'Fewer than 50 known TVT rows were provided. Some slope features will have limited history.',
    );
  }
  return warnings;
}

function cellToCsv(value: ManualWellRow[keyof ManualWellRow]): string {
  if (value === '' || value === null || value === undefined) {
    return '';
  }
  return String(value);
}

export function manualRowsToCsv(
  rows: ManualWellRow[],
  includeOptional: boolean,
): string {
  const columns: string[] = [...REQUIRED_COLUMNS];
  if (includeOptional) {
    const usedOptional = OPTIONAL_COLUMNS.filter((column) =>
      rows.some((row) => {
        const value = row[column];
        return value !== '' && value !== null && value !== undefined;
      }),
    );
    columns.push(...usedOptional);
  }

  const lines = [columns.join(',')];
  for (const row of rows) {
    lines.push(columns.map((column) => cellToCsv(row[column as keyof ManualWellRow])).join(','));
  }
  return `${lines.join('\n')}\n`;
}

export function sanitizeWellIdForFilename(wellId: string): string {
  const trimmed = wellId.trim() || 'manual_well';
  return trimmed.replace(/[^A-Za-z0-9_.\-]/g, '_');
}

export function manualRowsToFile(
  rows: ManualWellRow[],
  wellId: string,
  includeOptional = true,
): File {
  const safeId = sanitizeWellIdForFilename(wellId);
  const filename = `${safeId}__horizontal_well.csv`;
  const csv = manualRowsToCsv(rows, includeOptional);
  return new File([csv], filename, { type: 'text/csv' });
}

export function parseNumericCell(raw: string): number | '' | null {
  const trimmed = raw.trim();
  if (trimmed === '') {
    return '';
  }
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

export function parsePastedTable(text: string): ManualWellRow[] {
  const lines = text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    return [];
  }

  const delimiter = lines[0].includes('\t') ? '\t' : ',';
  const firstCells = lines[0].split(delimiter).map((cell) => cell.trim());
  const headerMap = new Map(
    firstCells.map((header, index) => [header.toUpperCase(), index]),
  );
  const hasHeader = REQUIRED_COLUMNS.some((column) =>
    headerMap.has(column.toUpperCase()),
  );

  const dataLines = hasHeader ? lines.slice(1) : lines;
  const indexOf = (name: string, fallback: number): number => {
    if (!hasHeader) {
      return fallback;
    }
    const found = headerMap.get(name.toUpperCase());
    return found ?? -1;
  };

  return dataLines.map((line) => {
    const cells = line.split(delimiter).map((cell) => cell.trim());
    const read = (name: string, fallback: number): number | '' => {
      const index = indexOf(name, fallback);
      if (index < 0 || index >= cells.length) {
        return '';
      }
      const parsed = parseNumericCell(cells[index] ?? '');
      return parsed === null ? '' : parsed;
    };

    const row = createEmptyManualRow({
      MD: read('MD', 0),
      GR: read('GR', 1),
      X: read('X', 2),
      Y: read('Y', 3),
      Z: read('Z', 4),
      TVT_input: read('TVT_input', 5),
    });

    (OPTIONAL_COLUMNS as readonly OptionalColumn[]).forEach((column, offset) => {
      row[column] = read(column, 6 + offset);
    });

    return row;
  });
}

export function createExampleManualRows(): ManualWellRow[] {
  const baseMd = 12000;
  const known = Array.from({ length: 12 }, (_, index) =>
    createEmptyManualRow({
      MD: baseMd + index,
      GR: 80 + index * 1.5,
      X: 2983500 + index * 0.2,
      Y: 1069000 + index * 0.2,
      Z: -9200 - index * 0.8,
      TVT_input: 11200 + index * 1.1,
    }),
  );
  const missing = Array.from({ length: 4 }, (_, index) =>
    createEmptyManualRow({
      MD: baseMd + 12 + index,
      GR: 95 + index,
      X: 2983502.4 + index * 0.2,
      Y: 1069002.4 + index * 0.2,
      Z: -9209.6 - index * 0.8,
      TVT_input: '',
    }),
  );
  return [...known, ...missing];
}

export function findPredictionBoundary(rows: ManualWellRow[]): {
  lastKnownIndex: number | null;
  firstPredictionIndex: number | null;
} {
  let lastKnownIndex: number | null = null;
  let firstPredictionIndex: number | null = null;
  rows.forEach((row, index) => {
    if (isEmptyTvt(row.TVT_input)) {
      if (firstPredictionIndex === null) {
        firstPredictionIndex = index;
      }
    } else {
      lastKnownIndex = index;
    }
  });
  return { lastKnownIndex, firstPredictionIndex };
}
