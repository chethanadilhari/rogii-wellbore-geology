# Rogii TVT Prediction Frontend

Local React application for predicting missing TVT values in the trailing section of a horizontal well. Talks only to the Phase 4 FastAPI backend.

## Stack

- React + TypeScript + Vite
- React Router
- TanStack Query
- React Hook Form + Zod
- Recharts
- Vitest + React Testing Library

## Installation

```bash
cd app/frontend
npm install
```

## Environment configuration

Copy `.env.example` to `.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

`http://localhost:8000` is also supported. Do not hard-code the API URL in components.

## Start the backend

From the repository root:

```bash
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
```

## Start the frontend

```bash
cd app/frontend
npm run dev
```

Expected URLs:

- Frontend: http://localhost:5173
- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

## CSV input mode

1. Open **Predict Well**
2. Choose **Upload CSV**
3. Drag/drop or browse a `.csv` with required columns `MD, GR, X, Y, Z, TVT_input`
4. Optionally set a custom well ID
5. Validate, then generate predictions
6. Review the chart/table and download both CSV outputs

Recommended smoke-test file:

```text
data/raw/test/000d7d20__horizontal_well.csv
```

Expected validation counts:

- Total rows: 5278
- Known rows: 1442
- Prediction rows: 3836

## Manual input mode

1. Choose **Manual Well Entry**
2. Enter a well ID
3. Add known TVT history rows first
4. Add one or more trailing rows with empty `TVT_input`
5. Optionally paste tabular data or load the built-in example
6. Validate and predict using the same multipart API endpoints

Manual mode converts the table into an in-memory `{well_id}__horizontal_well.csv` and posts it to `/validate`, `/predict`, and `/predict/full-well`.

## Validation workflow

`POST /validate` is authoritative. The UI shows:

- well ID, row counts, prediction interval
- reorder flag
- warnings
- structured API errors (`code`, `message`, `request_id`)

The **Generate Prediction** button stays disabled until backend validation succeeds.

## Prediction workflow

After a successful validation:

1. `POST /predict` → competition CSV (`id,tvt`)
2. `POST /predict/full-well` → full-well CSV with `predicted_tvt` and `prediction_source`
3. Parse the full-well response for chart/table display
4. Keep both response blobs for download (no browser-side regeneration)

## Downloads

- Competition: `{well_id}_submission.csv` (or `Content-Disposition` filename)
- Full well: `{well_id}_full_well_predictions.csv`

## Common errors

| Symptom | Likely cause |
|---------|--------------|
| API Offline in header | Backend not running or wrong `VITE_API_BASE_URL` |
| `NON_TRAILING_TVT_GAP` | Missing TVT values are not a clean trailing interval |
| `MISSING_REQUIRED_COLUMNS` | CSV lacks MD/GR/X/Y/Z/TVT_input |
| `NO_KNOWN_TVT` / `NO_PREDICTION_ROWS` | All missing or all known TVT_input |
| `UNSAFE_WELL_ID` | Illegal characters in well ID |
| Predict button disabled | Validation has not succeeded yet |

## Scripts

```bash
npm run dev
npm run build
npm run test
npm run preview
```
