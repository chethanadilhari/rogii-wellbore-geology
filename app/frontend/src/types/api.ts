export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  model_version: string | null;
  selected_model: string | null;
}

export interface ModelInfoResponse {
  model_version: string;
  selected_model: string;
  validation_rmse: number | null;
  validation_mae: number | null;
  feature_count: number;
  required_predictors: string[];
  optional_predictors: string[];
  alpha_last_known: number;
  weight_extra_trees: number;
  weight_xgboost: number;
  training_wells: number | null;
  final_fit_rows: number | null;
  created_at_utc: string | null;
}

export interface ValidateResponse {
  valid: boolean;
  well_id: string;
  total_rows: number;
  known_rows: number;
  prediction_rows: number;
  first_prediction_original_index: number | null;
  last_prediction_original_index: number | null;
  rows_reordered_for_processing: boolean;
  warnings: string[];
  errors: string[];
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}

export interface ApiErrorResponse {
  error: ApiErrorBody;
}

export interface PredictionHeaders {
  modelVersion: string | null;
  selectedModel: string | null;
  wellId: string | null;
  totalRows: number | null;
  knownRows: number | null;
  predictionRows: number | null;
  requestId: string | null;
  filename: string | null;
}

export interface PredictionResult {
  blob: Blob;
  text: string;
  headers: PredictionHeaders;
  filename: string;
}

export type PredictWorkflowState =
  | 'idle'
  | 'data_ready'
  | 'validating'
  | 'valid'
  | 'invalid'
  | 'predicting'
  | 'completed'
  | 'failed';

export type InputMode = 'upload' | 'manual';

export type ValidationStatus = 'valid' | 'warning' | 'invalid';
