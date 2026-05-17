from __future__ import annotations

from .core import (
    PRICING_TIERS,
    build_monthly_extras as build_monthly_extras_payload,
    optimize_request_data,
)
from .models import LoanRequest, OptimizationResponse


def optimize_loan(request: LoanRequest) -> OptimizationResponse:
    return OptimizationResponse.model_validate(optimize_request_data(request.model_dump()))


def build_monthly_extras(request: LoanRequest) -> dict[int, float]:
    return build_monthly_extras_payload(request.model_dump())
