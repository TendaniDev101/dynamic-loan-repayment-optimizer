from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class OneTimePayment(BaseModel):
    month: int = Field(ge=1)
    amount: float = Field(ge=0)


class ScenarioInput(BaseModel):
    global_extra_payment: float = Field(default=0, ge=0, allow_inf_nan=False)
    interval_extra_payment: float = Field(default=0, ge=0, allow_inf_nan=False)
    interval_months: int = Field(default=6, ge=1)
    one_time_payments: list[OneTimePayment] = Field(default_factory=list)
    monthly_extras: dict[int, float] = Field(default_factory=dict)

    @field_validator("monthly_extras")
    @classmethod
    def validate_monthly_extras(cls, value: dict[int, float]) -> dict[int, float]:
        for month, amount in value.items():
            if month < 1:
                raise ValueError("Monthly extra payment months must be at least 1.")
            if amount < 0:
                raise ValueError("Monthly extra payment amounts cannot be negative.")
        return value


class LoanRequest(BaseModel):
    principal: float = Field(gt=0, allow_inf_nan=False)
    term_months: int = Field(ge=1, le=360)
    credit_score: int | None = Field(default=None, ge=300, le=850)
    annual_rate: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    scenario: ScenarioInput = Field(default_factory=ScenarioInput)

    @model_validator(mode="after")
    def validate_scenario_bounds(self) -> "LoanRequest":
        if (self.credit_score is None) == (self.annual_rate is None):
            raise ValueError("Provide either a credit score or an annual interest rate.")

        if self.scenario.interval_months > self.term_months:
            raise ValueError("Recurring payment frequency cannot exceed the loan term.")

        for payment in self.scenario.one_time_payments:
            if payment.month > self.term_months:
                raise ValueError("One-time payment months cannot exceed the loan term.")

        for month in self.scenario.monthly_extras:
            if month > self.term_months:
                raise ValueError("Monthly extra payment months cannot exceed the loan term.")

        return self


class PricingDetails(BaseModel):
    pricing_method: Literal["credit_score", "manual_rate"]
    base_rate: float | None = None
    risk_premium: float | None = None
    total_annual_rate: float
    tier: str | None = None
    risk_category: str | None = None
    score_range: str | None = None
    manual_rate: float | None = None


class ScheduleRow(BaseModel):
    month: int
    opening_balance: float
    scheduled_payment: float
    interest_payment: float
    base_principal_payment: float
    extra_payment: float
    total_payment: float
    closing_balance: float


class LoanSummary(BaseModel):
    total_paid: float
    total_interest: float
    total_extra_paid: float
    actual_term_months: int
    monthly_payment: float
    annual_rate: float
    monthly_rate: float


class LoanScenarioResult(BaseModel):
    summary: LoanSummary
    schedule: list[ScheduleRow]


class DeltaSummary(BaseModel):
    total_paid_saved: float
    total_interest_saved: float
    months_saved: int


class OptimizationResponse(BaseModel):
    pricing: PricingDetails
    baseline: LoanScenarioResult
    optimized: LoanScenarioResult
    deltas: DeltaSummary
