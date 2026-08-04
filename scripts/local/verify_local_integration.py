#!/usr/bin/env python
"""Local integration + prediction-parity verifier for Phase 6.

Exercises a running FastAPI server (and optionally confirms the frontend URL),
then compares live API outputs to CLI / WellInferenceService / golden fixtures.

Usage (from repo root, with API already running):

    .\\.venv\\Scripts\\python.exe scripts\\local\\verify_local_integration.py
    python scripts/local/verify_local_integration.py --skip-frontend
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import urllib.error
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ATOL = 1e-6
SMOKE_WELL = PROJECT_ROOT / "data" / "raw" / "test" / "000d7d20__horizontal_well.csv"
GOLDEN_WELL = PROJECT_ROOT / "tests" / "fixtures" / "golden_well.csv"
GOLDEN_COMP = PROJECT_ROOT / "tests" / "fixtures" / "golden_competition_output.csv"
GOLDEN_FULL = PROJECT_ROOT / "tests" / "fixtures" / "golden_full_well_output.csv"
MANUAL_WELL = PROJECT_ROOT / "tmp" / "phase6_smoke" / "manual_well__horizontal_well.csv"

MANUAL_CSV = """MD,GR,X,Y,Z,TVT_input
12000,80,2983500,1069000,-9200,11200
12001,81.5,2983500.2,1069000.2,-9200.8,11201.1
12002,83,2983500.4,1069000.4,-9201.6,11202.2
12003,84.5,2983500.6,1069000.6,-9202.4,11203.3
12004,86,2983500.8,1069000.8,-9203.2,11204.4
12005,87.5,2983501,1069001,-9204,11205.5
12006,89,2983501.2,1069001.2,-9204.8,11206.6
12007,90.5,2983501.4,1069001.4,-9205.6,11207.7
12008,92,2983501.6,1069001.6,-9206.4,11208.8
12009,93.5,2983501.8,1069001.8,-9207.2,11209.9
12010,95,2983502,1069002,-9208,11211
12011,96.5,2983502.2,1069002.2,-9208.8,11212.1
12012,95,2983502.4,1069002.4,-9209.6,
12013,96,2983502.6,1069002.6,-9210.4,
12014,97,2983502.8,1069002.8,-9211.2,
12015,98,2983503,1069003,-9212,
"""


class Checker:
    def __init__(self) -> None:
        self.failed = 0
        self.passed = 0

    def ok(self, name: str, detail: str = "") -> None:
        self.passed += 1
        suffix = f": {detail}" if detail else ""
        print(f"[PASS] {name}{suffix}")

    def fail(self, name: str, detail: str = "") -> None:
        self.failed += 1
        suffix = f": {detail}" if detail else ""
        print(f"[FAIL] {name}{suffix}")

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.ok(name, detail)
        else:
            self.fail(name, detail)


def http_json(url: str, timeout: float = 10.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_status(url: str, timeout: float = 10.0) -> int:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return int(resp.status)


def multipart_post(
    url: str,
    file_path: Path,
    *,
    field_name: str = "file",
    well_id: str | None = None,
    timeout: float = 120.0,
) -> tuple[int, bytes, dict[str, str]]:
    """POST multipart/form-data without external deps (stdlib only)."""
    boundary = "----RogiiPhase6Boundary7MA4YWxkTrZu0gW"
    filename = file_path.name
    file_bytes = file_path.read_bytes()
    parts: list[bytes] = []
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{filename}"\r\n'
            f"Content-Type: text/csv\r\n\r\n"
        ).encode("utf-8")
        + file_bytes
        + b"\r\n"
    )
    if well_id:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="well_id"\r\n\r\n'
                f"{well_id}\r\n"
            ).encode("utf-8")
        )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return int(resp.status), resp.read(), headers
    except urllib.error.HTTPError as exc:
        headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        return int(exc.code), exc.read(), headers


def assert_allclose(a: pd.Series | np.ndarray, b: pd.Series | np.ndarray) -> None:
    np.testing.assert_allclose(
        np.asarray(a, dtype=float),
        np.asarray(b, dtype=float),
        atol=ATOL,
        rtol=0.0,
    )


def ensure_manual_well() -> Path:
    MANUAL_WELL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL_WELL.write_text(MANUAL_CSV, encoding="utf-8")
    return MANUAL_WELL


def run_cli_predict(well_path: Path, out_dir: Path, well_id: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    cmd = [
        python,
        str(PROJECT_ROOT / "scripts" / "predict_well.py"),
        "--input",
        str(well_path),
        "--output-dir",
        str(out_dir),
        "--overwrite",
    ]
    if well_id:
        cmd.extend(["--well-id", well_id])
    proc = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"CLI predict failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        )
    return out_dir / "submission.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6 local integration verifier")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-cli", action="store_true")
    args = parser.parse_args()

    check = Checker()
    api = args.api_base_url.rstrip("/")
    out_root = PROJECT_ROOT / "tmp" / "phase6_smoke"
    out_root.mkdir(parents=True, exist_ok=True)

    print("Phase 6 - local integration verification")
    print(f"  project:  {PROJECT_ROOT}")
    print(f"  api:      {api}")
    if not args.skip_frontend:
        print(f"  frontend: {args.frontend_url}")
    print()

    # --- Health / frontend connectivity ---
    try:
        health = http_json(f"{api}/health")
        check.check(
            "API /health",
            health.get("status") == "healthy" and health.get("model_loaded") is True,
            (
                f"status={health.get('status')} version={health.get('model_version')} "
                f"recipe={health.get('selected_model')}"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        check.fail("API /health", str(exc))
        print("\nAPI is not reachable. Start it first: .\\scripts\\local\\start-api.ps1")
        return 1

    try:
        model = http_json(f"{api}/models/current")
        check.check(
            "API /models/current",
            bool(model.get("model_version")),
            f"version={model.get('model_version')} selected={model.get('selected_model')}",
        )
    except Exception as exc:  # noqa: BLE001
        check.fail("API /models/current", str(exc))

    if not args.skip_frontend:
        try:
            status = http_get_status(args.frontend_url)
            check.check("Frontend reachable", status == 200, f"HTTP {status}")
        except Exception as exc:  # noqa: BLE001
            check.fail("Frontend reachable", str(exc))

    # --- CSV upload validate + both downloads (smoke well) ---
    if not SMOKE_WELL.is_file():
        check.fail("Smoke CSV present", str(SMOKE_WELL))
    else:
        status, body, _ = multipart_post(f"{api}/validate", SMOKE_WELL)
        if status != 200:
            check.fail("POST /validate (smoke)", f"HTTP {status}: {body[:300]!r}")
        else:
            payload = json.loads(body.decode("utf-8"))
            check.check(
                "POST /validate (smoke)",
                payload.get("total_rows") == 5278
                and payload.get("known_rows") == 1442
                and payload.get("prediction_rows") == 3836,
                (
                    f"total={payload.get('total_rows')} known={payload.get('known_rows')} "
                    f"pred={payload.get('prediction_rows')}"
                ),
            )

        status, body, headers = multipart_post(f"{api}/predict", SMOKE_WELL)
        smoke_comp_path = out_root / "api_smoke_submission.csv"
        if status != 200:
            check.fail("POST /predict (smoke)", f"HTTP {status}: {body[:300]!r}")
            api_smoke_comp = None
        else:
            smoke_comp_path.write_bytes(body)
            api_smoke_comp = pd.read_csv(BytesIO(body))
            check.check(
                "POST /predict (smoke)",
                len(api_smoke_comp) == 3836 and list(api_smoke_comp.columns) == ["id", "tvt"],
                f"rows={len(api_smoke_comp)} disposition={headers.get('content-disposition', '')}",
            )

        status, body, headers = multipart_post(f"{api}/predict/full-well", SMOKE_WELL)
        smoke_full_path = out_root / "api_smoke_full_well.csv"
        if status != 200:
            check.fail("POST /predict/full-well (smoke)", f"HTTP {status}: {body[:300]!r}")
            api_smoke_full = None
        else:
            smoke_full_path.write_bytes(body)
            api_smoke_full = pd.read_csv(BytesIO(body))
            check.check(
                "POST /predict/full-well (smoke)",
                len(api_smoke_full) == 5278
                and "predicted_tvt" in api_smoke_full.columns
                and "prediction_source" in api_smoke_full.columns,
                f"rows={len(api_smoke_full)} disposition={headers.get('content-disposition', '')}",
            )

        # CLI <-> API parity on smoke well
        if not args.skip_cli and api_smoke_comp is not None:
            try:
                cli_dir = out_root / "cli_smoke"
                cli_sub = run_cli_predict(SMOKE_WELL, cli_dir)
                cli_comp = pd.read_csv(cli_sub)
                assert_allclose(api_smoke_comp["tvt"], cli_comp["tvt"])
                check.check(
                    "CLI <-> API parity (smoke competition)",
                    api_smoke_comp["id"].tolist() == cli_comp["id"].tolist(),
                    f"rows={len(cli_comp)}",
                )
                if api_smoke_full is not None:
                    cli_full = pd.read_csv(cli_dir / "full_well_predictions.csv")
                    assert_allclose(api_smoke_full["predicted_tvt"], cli_full["predicted_tvt"])
                    check.ok("CLI <-> API parity (smoke full-well)")
            except Exception as exc:  # noqa: BLE001
                check.fail("CLI <-> API parity (smoke)", str(exc))

    # --- Manual well entry path (same multipart endpoints) ---
    manual_path = ensure_manual_well()
    status, body, _ = multipart_post(
        f"{api}/validate", manual_path, well_id="manual_well"
    )
    if status != 200:
        check.fail("POST /validate (manual)", f"HTTP {status}: {body[:300]!r}")
    else:
        payload = json.loads(body.decode("utf-8"))
        check.check(
            "POST /validate (manual)",
            payload.get("known_rows", 0) >= 1 and payload.get("prediction_rows", 0) >= 1,
            (
                f"well_id={payload.get('well_id')} known={payload.get('known_rows')} "
                f"pred={payload.get('prediction_rows')}"
            ),
        )

    status, body, _ = multipart_post(
        f"{api}/predict", manual_path, well_id="manual_well"
    )
    if status != 200:
        check.fail("POST /predict (manual)", f"HTTP {status}: {body[:300]!r}")
        api_manual_comp = None
    else:
        (out_root / "api_manual_submission.csv").write_bytes(body)
        api_manual_comp = pd.read_csv(BytesIO(body))
        check.check(
            "POST /predict (manual)",
            len(api_manual_comp) >= 1 and list(api_manual_comp.columns) == ["id", "tvt"],
            f"rows={len(api_manual_comp)}",
        )

    status, body, _ = multipart_post(
        f"{api}/predict/full-well", manual_path, well_id="manual_well"
    )
    if status != 200:
        check.fail("POST /predict/full-well (manual)", f"HTTP {status}: {body[:300]!r}")
    else:
        (out_root / "api_manual_full_well.csv").write_bytes(body)
        full = pd.read_csv(BytesIO(body))
        check.check(
            "POST /predict/full-well (manual)",
            "predicted_tvt" in full.columns and "prediction_source" in full.columns,
            f"rows={len(full)}",
        )

    if not args.skip_cli and api_manual_comp is not None:
        try:
            cli_dir = out_root / "cli_manual"
            cli_sub = run_cli_predict(manual_path, cli_dir, well_id="manual_well")
            cli_comp = pd.read_csv(cli_sub)
            assert_allclose(api_manual_comp["tvt"], cli_comp["tvt"])
            check.check(
                "CLI <-> API parity (manual)",
                api_manual_comp["id"].tolist() == cli_comp["id"].tolist(),
                f"rows={len(cli_comp)}",
            )
        except Exception as exc:  # noqa: BLE001
            check.fail("CLI <-> API parity (manual)", str(exc))

    # --- Golden fixture: service + API + frozen notebook-aligned outputs ---
    if GOLDEN_WELL.is_file() and (PROJECT_ROOT / "artifacts" / "v1").is_dir():
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "src"))
            from rogii_geo.inference.service import WellInferenceService

            service = WellInferenceService.from_artifact_root(
                PROJECT_ROOT / "artifacts",
                model_version="v1",
                verify_checksums=True,
            )
            well = pd.read_csv(GOLDEN_WELL)
            expected = service.predict_dataframe(well, "golden01")

            status, body, _ = multipart_post(
                f"{api}/predict",
                GOLDEN_WELL,
                well_id="golden01",
            )
            if status != 200:
                check.fail("POST /predict (golden)", f"HTTP {status}: {body[:300]!r}")
            else:
                api_comp = pd.read_csv(BytesIO(body))
                golden = pd.read_csv(GOLDEN_COMP)
                assert_allclose(api_comp["tvt"], expected.competition_output["tvt"])
                assert_allclose(api_comp["tvt"], golden["tvt"])
                check.ok(
                    "API <-> service <-> golden competition",
                    f"rows={len(api_comp)} (notebook/package SoT fixtures)",
                )

            status, body, _ = multipart_post(
                f"{api}/predict/full-well",
                GOLDEN_WELL,
                well_id="golden01",
            )
            if status != 200:
                check.fail("POST /predict/full-well (golden)", f"HTTP {status}")
            else:
                api_full = pd.read_csv(BytesIO(body))
                golden_full = pd.read_csv(GOLDEN_FULL)
                assert_allclose(api_full["predicted_tvt"], expected.full_well_output["predicted_tvt"])
                assert_allclose(api_full["predicted_tvt"], golden_full["predicted_tvt"])
                check.ok("API <-> service <-> golden full-well")

            if not args.skip_cli:
                with tempfile.TemporaryDirectory(prefix="rogii_cli_golden_") as tmp:
                    cli_sub = run_cli_predict(
                        GOLDEN_WELL, Path(tmp), well_id="golden01"
                    )
                    cli_comp = pd.read_csv(cli_sub)
                    assert_allclose(cli_comp["tvt"], golden["tvt"])
                    check.ok("CLI <-> golden competition")
        except Exception as exc:  # noqa: BLE001
            check.fail("Golden parity chain", str(exc))
    else:
        check.fail(
            "Golden artifacts available",
            "need tests/fixtures/golden_well.csv and artifacts/v1",
        )

    print()
    print(f"Passed: {check.passed}  Failed: {check.failed}")
    if check.failed:
        print("Phase 6 verification FAILED.")
        return 1
    print(
        "Phase 6 verification OK - notebook/package golden, CLI, API, and UI endpoints align."
    )
    print(
        "Frontend prediction path uses the same multipart endpoints verified above "
        "(upload + manual CSV -> /validate, /predict, /predict/full-well)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
