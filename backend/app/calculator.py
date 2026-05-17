from __future__ import annotations

from dataclasses import dataclass

from .models import (
    DeltaSummary,
    LoanRequest,
    LoanScenarioResult,
    LoanSummary,
    OptimizationResponse,
    PricingDetails,
    ScheduleRow,
)


@dataclass(frozen=True)
class PricingTier:
    tier: str
    score_min: int
    score_max: int
    risk_category: str
    risk_premium: float

    @property
    def score_range(self) -> str:
        return f"{self.score_min}-{self.score_max}"


BASE_RATE = 9.75
PRICING_TIERS = [
    PricingTier("AAA / Exceptional", 750, 850, "Minimum Risk", 0.50),
    PricingTier("A / Good", 680, 749, "Moderate Risk", 2.00),
    PricingTier("BB / Fair", 620, 679, "Managed Risk", 3.50),
    PricingTier("B / Below Average", 580, 619, "Elevated Risk", 5.50),
    PricingTier("C / High Risk", 300, 579, "High Risk", 8.00),
]
EPSILON = 1e-8


def optimize_loan(request: LoanRequest) -> OptimizationResponse:
    pricing = resolve_pricing(request.credit_score)
    baseline = build_scenario_result(
        principal=request.principal,
        term_months=request.term_months,
        annual_rate=pricing.total_annual_rate,
        scenario={},
    )
    optimized = build_scenario_result(
        principal=request.principal,
        term_months=request.term_months,
        annual_rate=pricing.total_annual_rate,
        scenario=build_monthly_extras(request),
    )
    deltas = DeltaSummary(
        total_paid_saved=round(baseline.summary.total_paid - optimized.summary.total_paid, 2),
        total_interest_saved=round(
            baseline.summary.total_interest - optimized.summary.total_interest,
            2,
        ),
        months_saved=baseline.summary.actual_term_months - optimized.summary.actual_term_months,
    )
    return OptimizationResponse(
        pricing=pricing,
        baseline=baseline,
        optimized=optimized,
        deltas=deltas,
    )


def resolve_pricing(credit_score: int) -> PricingDetails:
    for tier in PRICING_TIERS:
        if tier.score_min <= credit_score <= tier.score_max:
            total_annual_rate = round(BASE_RATE + tier.risk_premium, 2)
            return PricingDetails(
                base_rate=BASE_RATE,
                risk_premium=tier.risk_premium,
                total_annual_rate=total_annual_rate,
                tier=tier.tier,
                risk_category=tier.risk_category,
                score_range=tier.score_range,
            )
    raise ValueError("Unsupported credit score.")


def build_monthly_extras(request: LoanRequest) -> dict[int, float]:
    extras = {month: 0.0 for month in range(1, request.term_months + 1)}
    scenario = request.scenario

    for month in extras:
        extras[month] += scenario.global_extra_payment
        if scenario.interval_extra_payment and month % scenario.interval_months == 0:
            extras[month] += scenario.interval_extra_payment

    for payment in scenario.one_time_payments:
        if payment.month in extras:
            extras[payment.month] += payment.amount

    for month, amount in scenario.monthly_extras.items():
        if month in extras:
            extras[month] += amount

    return extras


def build_scenario_result(
    *,
    principal: float,
    term_months: int,
    annual_rate: float,
    scenario: dict[int, float],
) -> LoanScenarioResult:
    monthly_rate = annual_rate / 100 / 12
    monthly_payment = calculate_monthly_payment(principal, term_months, monthly_rate)

    balance = principal
    rows: list[ScheduleRow] = []
    total_paid = 0.0
    total_interest = 0.0
    total_extra_paid = 0.0

    for month in range(1, term_months + 1):
        opening_balance = balance
        interest_payment = opening_balance * monthly_rate
        scheduled_principal = min(monthly_payment - interest_payment, opening_balance)
        scheduled_payment = interest_payment + scheduled_principal

        requested_extra = max(scenario.get(month, 0.0), 0.0)
        max_extra = max(opening_balance - scheduled_principal, 0.0)
        extra_payment = min(requested_extra, max_extra)

        total_payment = scheduled_payment + extra_payment
        closing_balance = max(opening_balance - scheduled_principal - extra_payment, 0.0)

        rows.append(
            ScheduleRow(
                month=month,
                opening_balance=round(opening_balance, 2),
                scheduled_payment=round(scheduled_payment, 2),
                interest_payment=round(interest_payment, 2),
                base_principal_payment=round(scheduled_principal, 2),
                extra_payment=round(extra_payment, 2),
                total_payment=round(total_payment, 2),
                closing_balance=round(closing_balance, 2),
            )
        )

        total_paid += total_payment
        total_interest += interest_payment
        total_extra_paid += extra_payment
        balance = closing_balance

        if balance <= EPSILON:
            break

    summary = LoanSummary(
        total_paid=round(total_paid, 2),
        total_interest=round(total_interest, 2),
        total_extra_paid=round(total_extra_paid, 2),
        actual_term_months=len(rows),
        monthly_payment=round(monthly_payment, 2),
        annual_rate=round(annual_rate, 2),
        monthly_rate=round(monthly_rate * 100, 4),
    )
    return LoanScenarioResult(summary=summary, schedule=rows)


def calculate_monthly_payment(principal: float, term_months: int, monthly_rate: float) -> float:
    if monthly_rate == 0:
        return principal / term_months
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** (-term_months))

