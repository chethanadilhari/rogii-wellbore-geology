export function AboutPage() {
  return (
    <>
      <div className="page-header">
        <h1>About</h1>
        <p>
          Local application for predicting missing TVT values in the trailing
          section of a horizontal well.
        </p>
      </div>

      <div className="stack">
        <div className="card stack">
          <h2>Project name</h2>
          <p>Rogii Wellbore Geology — TVT Prediction</p>
        </div>

        <div className="card stack">
          <h2>Project objective</h2>
          <p>
            Provide a local engineering workflow to upload or enter horizontal
            well data, validate the trailing missing-TVT pattern, generate
            predictions with the production FastAPI model, review results, and
            download competition and full-well CSV outputs.
          </p>
        </div>

        <div className="card stack">
          <h2>Competition context</h2>
          <p>
            The prediction target aligns with a wellbore TVT imputation /
            competition-style submission format (`id,tvt`) for rows where
            `TVT_input` is missing.
          </p>
          <p className="help-text">
            Author, university, and supervisor details: placeholders pending
            project documentation.
          </p>
        </div>

        <div className="card stack">
          <h2>Technology stack</h2>
          <ul className="list-plain">
            <li>Frontend: React, TypeScript, Vite, React Router, TanStack Query, Recharts</li>
            <li>Backend: FastAPI wrapping the production `WellInferenceService`</li>
            <li>Model: last-known / residual blend with XGBoost residual correction</li>
          </ul>
        </div>

        <div className="card stack">
          <h2>Prediction target</h2>
          <p>
            Predict missing TVT values for the trailing section of a horizontal
            well. This application is not a geology classification system.
          </p>
        </div>

        <div className="card stack">
          <h2>Input assumptions</h2>
          <ul className="list-plain">
            <li>Required columns: MD, GR, X, Y, Z, TVT_input</li>
            <li>Known TVT values appear first, followed by one trailing missing interval</li>
            <li>Optional formation markers may be present but are not required</li>
            <li>The backend is the source of truth for validation and prediction</li>
          </ul>
        </div>

        <div className="card stack">
          <h2>Known limitations</h2>
          <ul className="list-plain">
            <li>One well per request; no batch ZIP uploads in this phase</li>
            <li>No authentication, persistence, or prediction history</li>
            <li>No model retraining or admin model switching from the UI</li>
            <li>Short known-TVT history may reduce prediction reliability</li>
          </ul>
        </div>
      </div>
    </>
  );
}
