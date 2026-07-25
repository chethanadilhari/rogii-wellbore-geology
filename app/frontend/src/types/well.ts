export const REQUIRED_COLUMNS = [
  'MD',
  'GR',
  'X',
  'Y',
  'Z',
  'TVT_input',
] as const;

export const OPTIONAL_COLUMNS = [
  'ANCC',
  'ASTNU',
  'ASTNL',
  'EGFDU',
  'EGFDL',
  'BUDA',
] as const;

export type RequiredColumn = (typeof REQUIRED_COLUMNS)[number];
export type OptionalColumn = (typeof OPTIONAL_COLUMNS)[number];

export type ManualCellValue = number | null | '';

export interface ManualWellRow {
  id: string;
  MD: ManualCellValue;
  GR: ManualCellValue;
  X: ManualCellValue;
  Y: ManualCellValue;
  Z: ManualCellValue;
  TVT_input: ManualCellValue;
  ANCC: ManualCellValue;
  ASTNU: ManualCellValue;
  ASTNL: ManualCellValue;
  EGFDU: ManualCellValue;
  EGFDL: ManualCellValue;
  BUDA: ManualCellValue;
}

export interface FullWellPredictionRow {
  original_row: number;
  MD: number | null;
  TVT_input: number | null;
  predicted_tvt: number | null;
  prediction_source: 'known' | 'model' | string;
}

export interface ChartSeriesPoint {
  MD: number;
  knownTvt: number | null;
  predictedTvt: number | null;
  predictionSource: string;
}
