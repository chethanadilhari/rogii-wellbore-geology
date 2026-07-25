"""Pydantic response schemas for the prediction API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str | None = None
    selected_model: str | None = None


class ModelInfoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_version: str
    selected_model: str
    validation_rmse: float | None = None
    validation_mae: float | None = None
    feature_count: int
    required_predictors: list[str]
    optional_predictors: list[str]
    alpha_last_known: float
    weight_extra_trees: float
    weight_xgboost: float
    training_wells: int | None = None
    final_fit_rows: int | None = None
    created_at_utc: str | None = None


class ValidateResponse(BaseModel):
    valid: bool
    well_id: str
    total_rows: int
    known_rows: int
    prediction_rows: int
    first_prediction_original_index: int | None = None
    last_prediction_original_index: int | None = None
    rows_reordered_for_processing: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody
