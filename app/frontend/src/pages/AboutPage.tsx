export function AboutPage() {
  return (
    <>
      <div className="page-header">
        <h1>About</h1>
        <p>
          ROGII Wellbore TVT Prediction - a supervised regression project for
          estimating missing True Vertical Thickness values in horizontal wells.
        </p>
      </div>

      <div className="stack">
        <div className="card stack">
          <h2>1. Project introduction</h2>
          <p>
            This project applies Computational Intelligence and Machine Learning
            to a wellbore geology prediction problem. The main objective is to
            predict missing True Vertical Thickness (TVT) values in the trailing
            section of horizontal wells.
          </p>
          <p>
            TVT is a continuous numerical value, so the task is treated as a
            supervised regression problem. The work covered data analysis,
            preprocessing, feature engineering, model development and comparison,
            model optimization, Kaggle evaluation, and finally a usable web
            application for TVT prediction.
          </p>
          <p>
            The selected model is served through a FastAPI backend and a React
            frontend, where users can provide well data, generate TVT
            predictions, visualise the results, and download the predicted
            outputs.
          </p>
        </div>

        <div className="card stack">
          <h2>2. Prediction problem</h2>
          <p>
            In each horizontal well, TVT information is available for the initial
            section. After a certain point, the <code>TVT_input</code> values are
            missing.
          </p>

          <div className="about-flow" aria-label="TVT prediction flow">
            <div className="about-flow-label">Beginning of well</div>
            <div className="about-flow-track">
              <span className="about-chip known">Known TVT</span>
              <span className="about-chip known">Known TVT</span>
              <span className="about-chip known">Known TVT</span>
              <span className="about-chip missing">Missing</span>
              <span className="about-chip missing">Missing</span>
              <span className="about-chip missing">Missing</span>
            </div>
            <div className="about-flow-footer">
              <span className="muted">End of well</span>
              <span className="about-flow-callout">
                Prediction starts where TVT_input becomes missing
              </span>
            </div>
          </div>

          <figure className="about-figure">
            <img
              src="/well-explanation.png"
              alt="Diagram of a vertical typewell and a horizontal well. The horizontal well has a known TVT_input section followed by a prediction region for missing TVT, with records paired by Well ID and geological context."
            />
            <figcaption>
              Vertical typewell (reference) and horizontal well: known{' '}
              <code>TVT_input</code> section, prediction region, and pairing by
              Well ID / geological context.
            </figcaption>
          </figure>

          <p>
            The model uses available well information and historical TVT values
            to estimate these missing TVT values. Because the expected output is
            a number (for example <code>10606.18</code>, <code>10607.53</code>,{' '}
            <code>10608.88</code>) rather than a category, this is regression,
            not classification.
          </p>
        </div>

        <div className="card stack">
          <h2>3. Dataset</h2>
          <p>
            The dataset mainly contains two types of files for each well:
          </p>
          <div className="card-grid">
            <div className="span-6">
              <div className="about-term-card">
                <h3>Horizontal Well</h3>
                <p>
                  The well for which TVT prediction is required - the
                  measurements for the well we want to predict.
                </p>
              </div>
            </div>
            <div className="span-6">
              <div className="about-term-card">
                <h3>Type Well</h3>
                <p>
                  Supporting / reference geological information used to
                  understand the geological structure around the horizontal
                  well.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card stack">
          <h2>4. Horizontal well columns</h2>
          <dl className="about-definition-list">
            <div>
              <dt>MD - Measured Depth</dt>
              <dd>
                Distance measured along the actual path of the well. Because a
                well can curve and become horizontal, MD is not simply vertical
                depth.
              </dd>
            </div>
            <div>
              <dt>GR - Gamma Ray</dt>
              <dd>
                Gamma Ray measurement that helps identify changes in the rock
                formations encountered by the well.
              </dd>
            </div>
            <div>
              <dt>X and Y</dt>
              <dd>
                Horizontal spatial coordinates describing the location and path
                of the well.
              </dd>
            </div>
            <div>
              <dt>Z</dt>
              <dd>
                Vertical / depth coordinate. Together, X + Y + Z describe the
                three-dimensional geometry of the well.
              </dd>
            </div>
          </dl>
        </div>

        <div className="card stack">
          <h2>5. What is TVT?</h2>
          <p>
            <strong>TVT</strong> means True Vertical Thickness. It represents
            the true vertical thickness through the geological formation.
          </p>
          <p className="help-text">
            MD tells us the distance along the well path. TVT represents the
            vertical geological thickness. TVT is the main target variable this
            project aims to predict.
          </p>
        </div>

        <div className="card stack">
          <h2>6. TVT vs TVT_input</h2>
          <p>These two columns have different roles:</p>
          <div className="card-grid">
            <div className="span-6">
              <div className="about-term-card">
                <h3>TVT</h3>
                <p>
                  The actual / reference True Vertical Thickness value when it
                  is available.
                </p>
              </div>
            </div>
            <div className="span-6">
              <div className="about-term-card">
                <h3>TVT_input</h3>
                <p>
                  The TVT information made available to the prediction process.
                  Known at the beginning of the well; missing toward the trailing
                  section.
                </p>
              </div>
            </div>
          </div>
          <p className="help-text">
            The model uses available historical <code>TVT_input</code> values
            and other well information to estimate the missing TVT values.
          </p>
        </div>

        <div className="card stack">
          <h2>7. Formation markers</h2>
          <p>
            The horizontal well data can also include formation-marker fields
            such as:
          </p>
          <ul className="about-tag-list" aria-label="Formation markers">
            <li>ANCC</li>
            <li>ASTNU</li>
            <li>ASTNL</li>
            <li>EGFDU</li>
            <li>EGFDL</li>
            <li>BUDA</li>
          </ul>
          <p>
            These represent geological formation markers or boundaries. They
            provide additional geological context about important formation
            positions around the well.
          </p>

          <div
            className="about-formation-depth"
            aria-label="Example formation marker depths from shallower to deeper"
          >
            <div className="about-formation-depth-label">Shallower</div>
            <ol className="about-formation-depth-list">
              <li>
                <span className="about-formation-dot" aria-hidden="true" />
                <span className="about-formation-name">Well position (Z)</span>
                <span className="about-formation-value">-9258.57</span>
                <span className="about-formation-note" />
              </li>
              <li>
                <span className="about-formation-dot" aria-hidden="true" />
                <span className="about-formation-name">ANCC</span>
                <span className="about-formation-value">-9395.81</span>
                <span className="about-formation-note" />
              </li>
              <li className="about-formation-boundary">
                <span className="about-formation-dot" aria-hidden="true" />
                <span className="about-formation-name">ASTNU</span>
                <span className="about-formation-value">-9569.86</span>
                <span className="about-formation-note">Upper boundary</span>
              </li>
              <li className="about-formation-boundary">
                <span className="about-formation-dot" aria-hidden="true" />
                <span className="about-formation-name">ASTNL</span>
                <span className="about-formation-value">-9597.64</span>
                <span className="about-formation-note">Lower boundary</span>
              </li>
              <li className="about-formation-boundary">
                <span className="about-formation-dot" aria-hidden="true" />
                <span className="about-formation-name">EGFDU</span>
                <span className="about-formation-value">-9670.99</span>
                <span className="about-formation-note">Upper boundary</span>
              </li>
              <li className="about-formation-boundary">
                <span className="about-formation-dot" aria-hidden="true" />
                <span className="about-formation-name">EGFDL</span>
                <span className="about-formation-value">-9705.96</span>
                <span className="about-formation-note">Lower boundary</span>
              </li>
              <li>
                <span className="about-formation-dot" aria-hidden="true" />
                <span className="about-formation-name">BUDA</span>
                <span className="about-formation-value">-9846.35</span>
                <span className="about-formation-note" />
              </li>
            </ol>
            <div className="about-formation-depth-label deeper">Deeper</div>
          </div>

          <p className="help-text">
            In short: ANCC, ASTNU, ASTNL, EGFDU, EGFDL, and BUDA are formation
            markers that describe important geological boundaries around the
            well. Depths become more negative as the well goes deeper.
          </p>
        </div>

        <div className="card stack">
          <h2>8. Type well</h2>
          <p>
            The Type Well provides supporting geological information from
            reference wells. It typically includes MD, TVT, GR, geological /
            formation information, and formation markers.
          </p>
          <p className="help-text">
            The horizontal well contains the measurements for the well where we
            need to predict TVT. The type well provides supporting geological
            information from reference wells.
          </p>
        </div>

        <div className="card stack">
          <h2>9. Why machine learning?</h2>
          <p>
            TVT changes with the well path and geological conditions. The
            relationship between MD, GR, spatial coordinates, geological
            information, and TVT can be complex and nonlinear.
          </p>
          <p>
            Machine-learning techniques were investigated to learn these
            relationships from historical well data and estimate TVT values in
            the missing section.
          </p>
        </div>

        <div className="card stack">
          <h2>10. Project workflow</h2>
          <ol className="workflow-list">
            <li>Understand the problem and dataset structure</li>
            <li>Analyse, preprocess, and engineer features from well data</li>
            <li>Develop and compare several machine-learning approaches</li>
            <li>Select and optimize the final model</li>
            <li>Evaluate with validation results and a Kaggle submission</li>
            <li>
              Deploy as a FastAPI + React application for prediction,
              visualisation, and download
            </li>
          </ol>
        </div>

        <div className="card stack">
          <h2>Technology stack</h2>
          <ul className="list-plain">
            <li>
              Frontend: React, TypeScript, Vite, React Router, TanStack Query,
              Recharts
            </li>
            <li>Backend: FastAPI wrapping the production inference service</li>
            <li>
              Model: last-known / residual blend with XGBoost residual
              correction
            </li>
          </ul>
        </div>

        <div className="card stack">
          <h2>Input assumptions</h2>
          <ul className="list-plain">
            <li>Required columns: MD, GR, X, Y, Z, TVT_input</li>
            <li>
              Known TVT values appear first, followed by one trailing missing
              interval
            </li>
            <li>
              Optional formation markers may be present but are not required
            </li>
            <li>
              The backend is the source of truth for validation and prediction
            </li>
          </ul>
        </div>

        <div className="card stack">
          <h2>Known limitations</h2>
          <ul className="list-plain">
            <li>One well per request; no batch ZIP uploads in this phase</li>
            <li>No authentication, persistence, or prediction history</li>
            <li>No model retraining or admin model switching from the UI</li>
            <li>
              Short known-TVT history may reduce prediction reliability
            </li>
          </ul>
        </div>
      </div>
    </>
  );
}
