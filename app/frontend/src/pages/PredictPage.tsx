import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { predictCompetition, predictFullWell } from '../api/prediction';
import { validateWell } from '../api/validation';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { StepIndicator } from '../components/common/StepIndicator';
import { LoadingBanner } from '../components/common/StatusBadge';
import { WellIdField } from '../components/common/WellIdField';
import { ManualWellTable } from '../components/manual-entry/ManualWellTable';
import { PredictionResults } from '../components/prediction/PredictionResults';
import { FileDropzone } from '../components/upload/FileDropzone';
import { ValidationSummary } from '../components/validation/ValidationSummary';
import { validateOptionalWellId, validateManualWellId } from '../utils/schemas';
import type {
  InputMode,
  PredictionResult,
  PredictWorkflowState,
  ValidateResponse,
  ValidationStatus,
} from '../types/api';
import type { ChartSeriesPoint, FullWellPredictionRow, ManualWellRow } from '../types/well';
import { parseFullWellPredictions, toChartSeries } from '../utils/csv';
import {
  getHistoryWarnings,
  manualRowsToFile,
} from '../utils/manualWell';

const WORKFLOW_STEPS = [
  { id: 'provide', label: 'Provide data' },
  { id: 'validate', label: 'Validate' },
  { id: 'predict', label: 'Predict' },
  { id: 'review', label: 'Review results' },
  { id: 'download', label: 'Download' },
];

function resolveValidationStatus(
  result: ValidateResponse | null,
  clientWarnings: string[],
): ValidationStatus | null {
  if (!result) return null;
  if (!result.valid) return 'invalid';
  if (clientWarnings.length > 0 || result.warnings.length > 0) return 'warning';
  return 'valid';
}

export function PredictPage() {
  const [mode, setMode] = useState<InputMode>('upload');
  const [workflow, setWorkflow] = useState<PredictWorkflowState>('idle');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [customWellId, setCustomWellId] = useState('');
  const [manualWellId, setManualWellId] = useState('manual_well');
  const [manualRows, setManualRows] = useState<ManualWellRow[]>([]);
  const [validation, setValidation] = useState<ValidateResponse | null>(null);
  const [clientWarnings, setClientWarnings] = useState<string[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [competition, setCompetition] = useState<PredictionResult | null>(null);
  const [fullWell, setFullWell] = useState<PredictionResult | null>(null);
  const [rows, setRows] = useState<FullWellPredictionRow[]>([]);
  const [chartData, setChartData] = useState<ChartSeriesPoint[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const resetDownstream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setValidation(null);
    setClientWarnings([]);
    setError(null);
    setCompetition(null);
    setFullWell(null);
    setRows([]);
    setChartData([]);
  }, []);

  const markDataReady = useCallback(
    (ready: boolean) => {
      resetDownstream();
      setWorkflow(ready ? 'data_ready' : 'idle');
    },
    [resetDownstream],
  );

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const activeFile = useMemo(() => {
    if (mode === 'upload') {
      return uploadFile;
    }
    if (manualRows.length === 0) {
      return null;
    }
    return manualRowsToFile(manualRows, manualWellId || 'manual_well');
  }, [mode, uploadFile, manualRows, manualWellId]);

  const wellIdForRequest =
    mode === 'upload' ? customWellId.trim() || undefined : manualWellId.trim();

  const validationStatus = resolveValidationStatus(validation, clientWarnings);

  const currentStepId = useMemo(() => {
    if (workflow === 'completed') return 'download';
    if (workflow === 'predicting' || workflow === 'failed') return 'predict';
    if (
      workflow === 'validating' ||
      workflow === 'valid' ||
      workflow === 'invalid'
    ) {
      return 'validate';
    }
    return 'provide';
  }, [workflow]);

  const completedStepIds = useMemo(() => {
    const completed: string[] = [];
    if (workflow !== 'idle') completed.push('provide');
    if (['valid', 'predicting', 'completed'].includes(workflow)) {
      completed.push('validate');
    }
    if (workflow === 'completed') {
      completed.push('predict', 'review', 'download');
    }
    return completed;
  }, [workflow]);

  const wellIdError =
    mode === 'upload'
      ? validateOptionalWellId(customWellId)
      : validateManualWellId(manualWellId);

  const canValidate =
    !!activeFile &&
    !wellIdError &&
    workflow !== 'validating' &&
    workflow !== 'predicting';

  const canPredict =
    validation?.valid === true &&
    (workflow === 'valid' || workflow === 'failed');

  const handleValidate = async () => {
    if (!activeFile || wellIdError) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setWorkflow('validating');
    setError(null);
    setCompetition(null);
    setFullWell(null);
    setRows([]);
    setChartData([]);

    try {
      const warnings =
        mode === 'manual' ? getHistoryWarnings(manualRows) : [];
      setClientWarnings(warnings);
      const result = await validateWell(
        activeFile,
        wellIdForRequest,
        controller.signal,
      );
      setValidation(result);
      setWorkflow('valid');
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      setValidation(null);
      setError(err);
      setWorkflow('invalid');
    }
  };

  const handlePredict = async () => {
    if (!activeFile || validation?.valid !== true) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setWorkflow('predicting');
    setError(null);

    try {
      const competitionResult = await predictCompetition(
        activeFile,
        wellIdForRequest,
        controller.signal,
      );
      const fullWellResult = await predictFullWell(
        activeFile,
        wellIdForRequest,
        controller.signal,
      );
      const parsedRows = parseFullWellPredictions(fullWellResult.text);
      setCompetition(competitionResult);
      setFullWell(fullWellResult);
      setRows(parsedRows);
      setChartData(toChartSeries(parsedRows));
      setWorkflow('completed');
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      setError(err);
      setWorkflow('failed');
    }
  };

  const handleReset = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setUploadFile(null);
    setCustomWellId('');
    setManualWellId('manual_well');
    setManualRows([]);
    resetDownstream();
    setWorkflow('idle');
  };

  return (
    <>
      <div className="page-header">
        <h1>Predict Well</h1>
        <p>
          Predict missing TVT values for the trailing section of a horizontal
          well.
        </p>
      </div>

      <StepIndicator
        steps={WORKFLOW_STEPS}
        currentStepId={currentStepId}
        completedStepIds={completedStepIds}
      />

      <div className="card stack">
        <div
          className="segmented"
          role="tablist"
          aria-label="Input mode"
        >
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'upload'}
            onClick={() => {
              if (mode === 'upload') return;
              setMode('upload');
              markDataReady(!!uploadFile);
            }}
          >
            Upload CSV
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'manual'}
            onClick={() => {
              if (mode === 'manual') return;
              setMode('manual');
              markDataReady(manualRows.length > 0);
            }}
          >
            Manual Well Entry
          </button>
        </div>

        {mode === 'upload' ? (
          <div className="stack">
            <FileDropzone
              file={uploadFile}
              onFileChange={(file) => {
                setUploadFile(file);
                markDataReady(!!file);
              }}
              disabled={workflow === 'validating' || workflow === 'predicting'}
            />
            <WellIdField
              value={customWellId}
              disabled={workflow === 'validating' || workflow === 'predicting'}
              onChange={(next) => {
                setCustomWellId(next);
                if (uploadFile) {
                  markDataReady(true);
                }
              }}
            />
          </div>
        ) : (
          <ManualWellTable
            wellId={manualWellId}
            onWellIdChange={(value) => {
              setManualWellId(value);
              markDataReady(manualRows.length > 0);
            }}
            rows={manualRows}
            onRowsChange={(nextRows) => {
              setManualRows(nextRows);
              markDataReady(nextRows.length > 0);
            }}
            disabled={workflow === 'validating' || workflow === 'predicting'}
          />
        )}
      </div>

      <div className="card stack">
        <h2>Step 2 — Validate</h2>
        <div className="row">
          <button
            type="button"
            className="btn"
            disabled={!canValidate}
            aria-busy={workflow === 'validating'}
            onClick={() => {
              void handleValidate();
            }}
          >
            {workflow === 'validating' ? 'Validating…' : 'Validate well'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleReset}
          >
            Reset workflow
          </button>
        </div>
        {workflow === 'validating' ? (
          <LoadingBanner label="Validating well data against the API…" />
        ) : null}
        {workflow === 'invalid' && error ? (
          <ErrorAlert error={error} title="Validation failed" />
        ) : null}
        <ValidationSummary
          result={validation}
          status={validationStatus}
          clientWarnings={clientWarnings}
        />
      </div>

      <div className="card stack">
        <h2>Step 3 — Predict</h2>
        <button
          type="button"
          className="btn"
          disabled={!canPredict}
          aria-busy={workflow === 'predicting'}
          onClick={() => {
            void handlePredict();
          }}
        >
          {workflow === 'predicting'
            ? 'Generating TVT predictions…'
            : 'Generate Prediction'}
        </button>
        {workflow === 'predicting' ? (
          <LoadingBanner label="Generating TVT predictions" />
        ) : null}
        {workflow === 'failed' && error ? (
          <ErrorAlert
            error={error}
            title="Prediction failed"
            onRetry={() => {
              void handlePredict();
            }}
          />
        ) : null}
        {!validation?.valid ? (
          <p className="help-text">
            The Predict button remains disabled until backend validation
            succeeds.
          </p>
        ) : null}
      </div>

      {workflow === 'completed' &&
      validation &&
      competition &&
      fullWell ? (
        <div className="card stack">
          <h2>Steps 4–5 — Review and download</h2>
          <PredictionResults
            validation={validation}
            competition={competition}
            fullWell={fullWell}
            rows={rows}
            chartData={chartData}
          />
        </div>
      ) : null}
    </>
  );
}
