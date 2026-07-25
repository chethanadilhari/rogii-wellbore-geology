import { describe, expect, it } from 'vitest';
import { countCsvDataRows, parseFullWellPredictions, toChartSeries } from './csv';

describe('csv utilities', () => {
  it('parses full-well predictions for chart and table', () => {
    const text = [
      'MD,TVT_input,predicted_tvt,prediction_source',
      '1,10,10,known',
      '2,,12.5,model',
    ].join('\n');

    const rows = parseFullWellPredictions(text);
    expect(rows).toHaveLength(2);
    expect(rows[0].prediction_source).toBe('known');
    expect(rows[1].predicted_tvt).toBe(12.5);

    const chart = toChartSeries(rows);
    expect(chart[0].knownTvt).toBe(10);
    expect(chart[0].predictedTvt).toBeNull();
    expect(chart[1].predictedTvt).toBe(12.5);
    expect(countCsvDataRows(text)).toBe(2);
  });
});
