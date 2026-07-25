import { describe, expect, it } from 'vitest';
import {
  countKnownTvtRows,
  createEmptyManualRow,
  createExampleManualRows,
  getHistoryWarnings,
  isEmptyTvt,
  manualRowsToCsv,
  manualRowsToFile,
  parsePastedTable,
} from './manualWell';

describe('manual well utilities', () => {
  it('marks empty TVT as prediction rows', () => {
    const known = createEmptyManualRow({ TVT_input: 100 });
    const missing = createEmptyManualRow({ TVT_input: '' });
    expect(isEmptyTvt(known.TVT_input)).toBe(false);
    expect(isEmptyTvt(missing.TVT_input)).toBe(true);
  });

  it('loads an example with known rows followed by missing rows', () => {
    const rows = createExampleManualRows();
    expect(countKnownTvtRows(rows)).toBeGreaterThanOrEqual(10);
    expect(rows.some((row) => isEmptyTvt(row.TVT_input))).toBe(true);
    const firstMissing = rows.findIndex((row) => isEmptyTvt(row.TVT_input));
    expect(rows.slice(0, firstMissing).every((row) => !isEmptyTvt(row.TVT_input))).toBe(
      true,
    );
  });

  it('converts the manual table into CSV correctly', () => {
    const rows = [
      createEmptyManualRow({
        MD: 1,
        GR: 2,
        X: 3,
        Y: 4,
        Z: 5,
        TVT_input: 6,
      }),
      createEmptyManualRow({
        MD: 2,
        GR: 2,
        X: 3,
        Y: 4,
        Z: 5,
        TVT_input: '',
      }),
    ];
    const csv = manualRowsToCsv(rows, false);
    expect(csv.split('\n')[0]).toBe('MD,GR,X,Y,Z,TVT_input');
    expect(csv).toContain('1,2,3,4,5,6');
    expect(csv).toContain('2,2,3,4,5,');
  });

  it('creates a safe multipart filename', () => {
    const file = manualRowsToFile(createExampleManualRows(), 'Demo Well');
    expect(file.name).toBe('Demo_Well__horizontal_well.csv');
    expect(file.type).toBe('text/csv');
  });

  it('parses pasted tabular data', () => {
    const pasted = parsePastedTable(
      'MD,GR,X,Y,Z,TVT_input\n10,1,2,3,4,5\n11,1,2,3,4,',
    );
    expect(pasted).toHaveLength(2);
    expect(pasted[0].MD).toBe(10);
    expect(pasted[1].TVT_input).toBe('');
  });

  it('emits non-blocking history warnings', () => {
    const short = Array.from({ length: 5 }, (_, index) =>
      createEmptyManualRow({ TVT_input: index + 1 }),
    );
    expect(getHistoryWarnings(short)[0]).toMatch(/Fewer than 10/);
  });
});
