# Rogii Wellbore Geology

Project for wellbore geology analysis and modeling.

## Project Structure

```
rogii-wellbore-geology/
├── data/
│   ├── raw/train/     # {well_id}__horizontal_well.csv (+ optional typewell)
│   ├── raw/test/
│   └── processed/
├── notebooks/         # Research history (FinalProductionCandidate = ensemble residual notebook)
├── src/rogii_geo/     # Production package (features, training, inference)
├── app/api/           # FastAPI one-well prediction backend (Phase 4)
├── app/frontend/      # React/Vite local UI (Phase 5)
├── scripts/           # CLI entry points (train_export, predict_well)
├── artifacts/         # Versioned model bundles (gitignored binaries)
├── models/            # Legacy notebook joblibs
├── results/           # Notebook metrics / metadata
├── tests/
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install -e .
```

## Prediction task

Predict `TVT` only where `TVT_input` is missing (trailing hidden section).

**Production recipe (frozen):** `blend_lastknown_0.70_ensemble`

```text
xgb_tvt = linear_tvt_projection + xgb_predicted_residual
final_tvt = 0.70 * last_known_tvt + 0.30 * xgb_tvt
```

Extra Trees is optional (`weight_extra_trees = 0` in the active config).

## FastAPI backend (Phase 4)

Local one-well prediction API wrapping `WellInferenceService`. No training at request time.

### Environment

Copy `.env.example` to `.env` and adjust as needed:

```env
MODEL_ARTIFACT_ROOT=artifacts
MODEL_VERSION=
VERIFY_ARTIFACT_CHECKSUMS=true
MAX_UPLOAD_MB=25
MAX_ROWS_PER_WELL=100000
API_HOST=127.0.0.1
API_PORT=8000
API_LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

- Empty `MODEL_VERSION` resolves through `artifacts/current.json`.
- Checksum verification is enabled by default; startup fails if artifacts are missing or corrupted.
- CORS allows only the configured local frontend origins (not `*`).

### Start the API

```bash
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
# or
python -m uvicorn app.api.main:app --reload
```

OpenAPI docs: `http://127.0.0.1:8000/docs` and `/redoc`.

### Endpoints

| Method | Path | Response |
|--------|------|----------|
| GET | `/health` | JSON readiness (`model_loaded`, version, recipe) |
| GET | `/models/current` | Safe model card / ensemble metadata |
| POST | `/validate` | JSON validation summary (no prediction) |
| POST | `/predict` | Downloadable competition CSV (`id,tvt`) |
| POST | `/predict/full-well` | Downloadable full-well CSV |

Multipart field: `file` (required). Optional form field: `well_id`.

### Sample curl

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/models/current

curl -X POST -F "file=@data/raw/test/000d7d20__horizontal_well.csv" \
  http://127.0.0.1:8000/validate

curl -X POST -F "file=@data/raw/test/000d7d20__horizontal_well.csv" \
  http://127.0.0.1:8000/predict --output api_submission.csv

curl -X POST -F "file=@data/raw/test/000d7d20__horizontal_well.csv" \
  http://127.0.0.1:8000/predict/full-well --output api_full_well.csv
```

Prediction responses include headers such as `X-Model-Version`, `X-Well-Id`, `X-Prediction-Rows`, and `X-Request-ID`.

## React frontend (Phase 5)

Local desktop-focused UI for one-well validation, prediction, review, and download. No browser-side ML.

### Install and configure

```bash
cd app/frontend
npm install
copy .env.example .env   # Windows
# VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Run locally

Terminal 1 (API):

```bash
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 (UI):

```bash
cd app/frontend
npm run dev
```

- Frontend: `http://localhost:5173`
- API: `http://127.0.0.1:8000`
- OpenAPI: `http://127.0.0.1:8000/docs`

### Pages

| Page | Purpose |
|------|---------|
| Dashboard | Model summary from `/models/current` + `/health`, workflow overview |
| Predict Well | Upload CSV or manual well entry → validate → predict → chart/table → downloads |
| Model Information | Recipe, metrics, predictors, artifact status |
| About | Objective, assumptions, limitations |

### Input modes

Both modes call the same multipart endpoints (`file`, optional `well_id`):

1. **Upload CSV** — drag/drop or browse `.csv`
2. **Manual Well Entry** — editable known-history + trailing missing `TVT_input` table converted to an in-memory CSV

### Frontend tests

```bash
cd app/frontend
npm run test
npm run build
```

See `app/frontend/README.md` for validation/prediction/download details and common errors.

### Error format

```json
{
  "error": {
    "code": "NON_TRAILING_TVT_GAP",
    "message": "...",
    "details": {},
    "request_id": "..."
  }
}
```

Common codes: `INVALID_UPLOAD`, `FILE_TOO_LARGE`, `EMPTY_FILE`, `INVALID_CSV`, `DUPLICATE_COLUMNS`, `MISSING_REQUIRED_COLUMNS`, `INVALID_MD`, `NO_KNOWN_TVT`, `NO_PREDICTION_ROWS`, `NON_TRAILING_TVT_GAP`, `UNSAFE_WELL_ID`, `ROW_LIMIT_EXCEEDED`, `MODEL_UNAVAILABLE`, `PREDICTION_FAILED`, `INTERNAL_ERROR`.

### Input schema

Same as the CLI: required `MD, GR, X, Y, Z, TVT_input` with a clean trailing missing-`TVT_input` interval.

## Predict one well (Phase 3)

```bash
python scripts/predict_well.py \
  --input data/raw/test/000d7d20__horizontal_well.csv \
  --output-dir predictions/000d7d20
```

Equivalent module form:

```bash
python -m scripts.predict_well \
  --input data/raw/test/000d7d20__horizontal_well.csv \
  --output-dir predictions/000d7d20
```

### Input schema

Required columns:

```text
MD, GR, X, Y, Z, TVT_input
```

Optional columns may include formation markers (`ANCC`, `ASTNU`, `ASTNL`, `EGFDU`, `EGFDL`, `BUDA`) and `TVT`.

### Validation assumptions

- File must exist, be a `.csv`, and contain at least one data row.
- Duplicate column names are rejected.
- `MD` must be present and fully numeric (no missing values).
- There must be a known `TVT_input` prefix and a trailing missing interval.
- Non-trailing missing intervals are rejected (not silently repaired).
- Rows are stably sorted by `MD` internally; competition IDs use the original row index.
- Well ID is taken from `--well-id`, else `{well_id}__horizontal_well.csv`, else the filename stem (sanitized).

### Outputs

| File | Contents |
|------|----------|
| `submission.csv` | Competition format: `id,tvt` for missing-`TVT_input` rows only |
| `full_well_predictions.csv` | All original columns + `predicted_tvt`, `prediction_source` (`known` / `model`) |
| `prediction_summary.json` | Machine-readable run summary (counts, stats, checksums, timing) |

Competition IDs are `{well_id}_{original_row_index}`.

### Model resolution

1. `--model-version` when supplied
2. Otherwise `artifacts/current.json`
3. Fail if neither a version nor a valid active pointer exists

Default `--artifact-root` is `artifacts/`.

### Overwrite behavior

Existing output files cause a failure unless `--overwrite` is passed. Unrelated files in the output directory are left untouched.

### Checksum verification

Artifact checksums are verified by default. `--skip-checksum-verification` is debug-only and prints a visible warning.

### Common failures

| Message pattern | Meaning |
|-----------------|--------|
| `Input file not found` | Bad `--input` path |
| `Missing required columns` | Schema incomplete |
| `No known-prefix rows` | Entirely missing `TVT_input` |
| `No prediction rows` | Entirely known `TVT_input` |
| `clean trailing mask` | Non-trailing missing interval |
| `Output already exists` | Pass `--overwrite` |
| `Active model pointer not found` | Missing `current.json` and no `--model-version` |
| `Unsafe well ID` | Path separators or illegal characters |

### Inspecting the summary

```bash
python -c "import json; print(json.load(open('predictions/000d7d20/prediction_summary.json', encoding='utf-8')))"
```

Useful fields: `well_id`, `model_version`, `selected_model`, `known_rows`, `prediction_rows`, `prediction_min/max/mean`, `checksum_verification`, `rows_reordered_internally`, `warnings`.

### Useful CLI flags

```text
--artifact-root
--model-version
--well-id
--competition-filename
--full-well-filename
--summary-filename
--overwrite
--skip-checksum-verification
--log-level
```

## Train and export artifacts (Phase 2)

Training data layout (either works):

```text
data/raw/train/{well_id}__horizontal_well.csv
# or
data/train/{well_id}__horizontal_well.csv
```

Run:

```bash
python scripts/train_export.py
# or
python -m scripts.train_export
```

Useful flags:

```bash
python scripts/train_export.py --model-version v1 --overwrite
python scripts/train_export.py --include-optional-extra-trees
python scripts/train_export.py --fit-max-rows 150000 --max-hidden-rows 400
```

### Artifact bundle layout

```text
artifacts/<model_version>/
  xgboost_residual.json          # native XGBoost save_model
  feature_columns.json
  feature_medians.json
  ensemble_config.json
  model_card.json
  manifest.json                  # SHA-256 checksums (excludes itself)
  validation_comparison.csv
  per_well_validation_metrics.csv
  training_dataset_summary.csv
  mask_summary.csv
  extra_trees_residual.joblib    # only if trained/exported
```

Active model pointer (portable on Windows):

```text
artifacts/current.json
```

```json
{ "model_version": "v1", "updated_at_utc": "..." }
```

The pointer is updated only after training, checksum verification, and reload parity succeed.

### Inspect the active model

```bash
python -c "from pathlib import Path; from rogii_geo.models.artifact_loader import resolve_artifact_dir, load_artifact_bundle; b=load_artifact_bundle(resolve_artifact_dir(Path('artifacts'))); print(b.metadata)"
```

### Verify checksums

Checksums are verified automatically by `load_artifact_bundle(..., verify=True)`.

### Optional Extra Trees

By default Extra Trees is **not** trained when `weight_extra_trees == 0`. To export it for research:

```bash
python scripts/train_export.py --include-optional-extra-trees
```

### Git warning

`artifacts/` is gitignored. Do **not** commit large model binaries (`xgboost_residual.json`, joblibs). Keep metadata copies under `results/` if you need reviewable history. Local `predictions/` outputs are also gitignored.

## Package tests

```bash
python -m pytest tests -v
```

Golden inference fixtures live under `tests/fixtures/` and exercise `artifacts/v1` when present.

## Notebook order (research history)

1. `01`–`04` — understanding, EDA, baselines (Last Known TVT)
2. `05`–`07B` — absolute-TVT ML / ensemble (legacy for competition scoring)
3. `08`–`09` — absolute-TVT Kaggle path (superseded; leaky `TVT_input` feature)
4. `10` / `final_kaggle_submission` — trailing-mask residual redesign
5. **`final_ensemble_residual_kaggle_submission.ipynb`** — FinalProductionCandidate / best Kaggle recipe

## Folder roles

- `src/rogii_geo/` — shared production code (do not duplicate FE into notebooks/CLIs)
- `app/api/` — FastAPI one-well backend reusing `WellInferenceService`
- `app/frontend/` — React/Vite UI for local validation, prediction, and downloads
- `scripts/train_export.py` — offline training + artifact export
- `scripts/predict_well.py` — one-well production inference CLI
- `artifacts/` — immutable versioned inference bundles
- `notebooks/` — exploratory history; not the inference runtime
