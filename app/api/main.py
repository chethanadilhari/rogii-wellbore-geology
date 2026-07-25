"""FastAPI application factory and lifespan for one-well TVT prediction."""

from __future__ import annotations

import logging
import re
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.config import Settings, get_settings
from app.api.dependencies import build_safe_model_info
from app.api.errors import ApiError, api_error_handler, unhandled_error_handler
from app.api.routes import health, models, prediction, validation
from rogii_geo import __version__ as PACKAGE_VERSION
from rogii_geo.inference.service import WellInferenceService

logger = logging.getLogger(__name__)

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,127}$")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API application, optionally with injected settings (tests)."""

    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(
            level=getattr(logging, cfg.api_log_level, logging.INFO),
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
        logger.info(
            "Loading artifacts from %s (version=%s verify=%s)",
            cfg.model_artifact_root,
            cfg.model_version or "current.json",
            cfg.verify_artifact_checksums,
        )
        try:
            service = WellInferenceService.from_artifact_root(
                cfg.model_artifact_root,
                model_version=cfg.model_version,
                verify_checksums=cfg.verify_artifact_checksums,
            )
        except Exception:
            logger.exception("Failed to load production artifact bundle at startup")
            raise

        model_info = build_safe_model_info(service)
        app.state.settings = cfg
        app.state.inference_service = service
        app.state.model_info = model_info
        logger.info(
            "Model ready version=%s selected_model=%s feature_count=%s",
            model_info.model_version,
            model_info.selected_model,
            model_info.feature_count,
        )
        try:
            yield
        finally:
            app.state.inference_service = None
            app.state.model_info = None
            logger.info("Prediction service shut down")

    application = FastAPI(
        title="ROGII Wellbore TVT Prediction API",
        version=PACKAGE_VERSION,
        description=(
            "Local one-well inference API for trailing-mask TVT prediction using "
            "the frozen production recipe blend_lastknown_0.70_ensemble. "
            "No training occurs at request time."
        ),
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Model-Version",
            "X-Selected-Model",
            "X-Well-Id",
            "X-Total-Rows",
            "X-Known-Rows",
            "X-Prediction-Rows",
            "Content-Disposition",
        ],
    )

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "").strip()
        if incoming and _SAFE_REQUEST_ID.fullmatch(incoming):
            request_id = incoming
        else:
            request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(Exception, unhandled_error_handler)

    application.include_router(health.router)
    application.include_router(models.router)
    application.include_router(validation.router)
    application.include_router(prediction.router)

    return application


app = create_app()
