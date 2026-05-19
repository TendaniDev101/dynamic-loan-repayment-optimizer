from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


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
TERM_OPTIONS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]
PRICING_TIERS = [
    PricingTier("AAA / Exceptional", 750, 850, "Minimum Risk", 0.50),
    PricingTier("A / Good", 680, 749, "Moderate Risk", 2.00),
    PricingTier("BB / Fair", 620, 679, "Managed Risk", 3.50),
    PricingTier("B / Below Average", 580, 619, "Elevated Risk", 5.50),
    PricingTier("C / High Risk", 300, 579, "High Risk", 8.00),
]
EPSILON = 1e-8


class LoanValidationError(ValueError):
    pass


def get_config_payload() -> dict[str, object]:
    return {
        "term_options": TERM_OPTIONS,
        "repayment_strategies": [
            {
                "value": "term_reduction",
                "label": "Pay Off Faster",
            },
            {
                "value": "payment_recast",
                "label": "Lower My Monthly Payment",
            },
        ],
        "pricing_tiers": [
            {
                "tier": tier.tier,
                "score_min": tier.score_min,
                "score_max": tier.score_max,
                "risk_category": tier.risk_category,
                "risk_premium": tier.risk_premium,
            }
            for tier in PRICING_TIERS
        ],
    }


def optimize_request_data(payload: dict[str, Any]) -> dict[str, object]:
    request = normalize_request(payload)
    pricing = resolve_pricing(request)
    baseline = build_scenario_result(
        principal=request["principal"],
        term_months=request["term_months"],
        annual_rate=pricing["total_annual_rate"],
        monthly_service_fee=request["monthly_service_fee"],
        repayment_strategy="term_reduction",
        scenario={},
    )
    optimized = build_scenario_result(
        principal=request["principal"],
        term_months=request["term_months"],
        annual_rate=pricing["total_annual_rate"],
        monthly_service_fee=request["monthly_service_fee"],
        repayment_strategy=request["repayment_strategy"],
        scenario=build_monthly_extras(request),
    )
    deltas = {
        "total_paid_saved": round(
            baseline["summary"]["total_paid"] - optimized["summary"]["total_paid"],
            2,
        ),
        "total_interest_saved": round(
            baseline["summary"]["total_interest"] - optimized["summary"]["total_interest"],
            2,
        ),
        "months_saved": (
            baseline["summary"]["actual_term_months"]
            - optimized["summary"]["actual_term_months"]
        ),
    }
    return {
        "repayment_strategy": request["repayment_strategy"],
        "pricing": pricing,
        "baseline": baseline,
        "optimized": optimized,
        "deltas": deltas,
    }


def normalize_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LoanValidationError("Request body must be a JSON object.")

    principal = parse_number(payload.get("principal"), "Principal")
    if principal <= 0:
        raise LoanValidationError("Principal must be greater than zero.")

    monthly_service_fee = parse_number(
        payload.get("monthly_service_fee", 0),
        "Monthly service fee",
    )
    if monthly_service_fee < 0:
        raise LoanValidationError("Monthly service fee cannot be negative.")

    repayment_strategy = payload.get("repayment_strategy", "term_reduction")
    if repayment_strategy not in {"term_reduction", "payment_recast"}:
        raise LoanValidationError("Repayment strategy is not supported.")

    term_months = parse_int(payload.get("term_months"), "Term")
    if term_months < 1 or term_months > 360:
        raise LoanValidationError("Term must be between 1 and 360 months.")

    credit_score_raw = payload.get("credit_score")
    annual_rate_raw = payload.get("annual_rate")
    has_credit_score = value_is_present(credit_score_raw)
    has_annual_rate = value_is_present(annual_rate_raw)
    if has_credit_score == has_annual_rate:
        raise LoanValidationError("Provide either a credit score or an annual interest rate.")

    credit_score = None
    annual_rate = None
    if has_credit_score:
        credit_score = parse_int(credit_score_raw, "Credit score")
        if credit_score < 300 or credit_score > 850:
            raise LoanValidationError("Credit score must be between 300 and 850.")
    else:
        annual_rate = parse_number(annual_rate_raw, "Annual interest rate")
        if annual_rate < 0:
            raise LoanValidationError("Annual interest rate cannot be negative.")

    scenario_raw = payload.get("scenario") or {}
    if not isinstance(scenario_raw, dict):
        raise LoanValidationError("Scenario must be a JSON object.")

    global_extra_payment = parse_number(
        scenario_raw.get("global_extra_payment", 0),
        "Recurring extra repayment",
    )
    if global_extra_payment < 0:
        raise LoanValidationError("Recurring extra repayment cannot be negative.")

    interval_extra_payment = parse_number(
        scenario_raw.get("interval_extra_payment", 0),
        "Interval extra repayment",
    )
    if interval_extra_payment < 0:
        raise LoanValidationError("Interval extra repayment cannot be negative.")

    interval_months = parse_int(
        scenario_raw.get("interval_months", 6),
        "Recurring payment frequency",
    )
    if interval_months < 1:
        raise LoanValidationError("Recurring payment frequency must be at least 1 month.")
    if interval_months > term_months:
        raise LoanValidationError("Recurring payment frequency cannot exceed the loan term.")

    one_time_payments_raw = scenario_raw.get("one_time_payments", [])
    if not isinstance(one_time_payments_raw, list):
        raise LoanValidationError("One-time payments must be a list.")
    one_time_payments = []
    for index, payment in enumerate(one_time_payments_raw, start=1):
        if not isinstance(payment, dict):
            raise LoanValidationError(f"One-time payment {index} must be an object.")
        month = parse_int(payment.get("month"), f"One-time payment {index} month")
        if month < 1 or month > term_months:
            raise LoanValidationError("One-time payment months cannot exceed the loan term.")
        amount = parse_number(payment.get("amount"), f"One-time payment {index} amount")
        if amount < 0:
            raise LoanValidationError("One-time payment amounts cannot be negative.")
        one_time_payments.append({"month": month, "amount": amount})

    monthly_extras_raw = scenario_raw.get("monthly_extras", {})
    if not isinstance(monthly_extras_raw, dict):
        raise LoanValidationError("Monthly extra payments must be a JSON object.")
    monthly_extras: dict[int, float] = {}
    for raw_month, raw_amount in monthly_extras_raw.items():
        month = parse_int(raw_month, "Monthly extra payment month")
        if month < 1 or month > term_months:
            raise LoanValidationError("Monthly extra payment months cannot exceed the loan term.")
        amount = parse_number(raw_amount, "Monthly extra payment amount")
        if amount < 0:
            raise LoanValidationError("Monthly extra payment amounts cannot be negative.")
        monthly_extras[month] = amount

    return {
        "principal": principal,
        "term_months": term_months,
        "credit_score": credit_score,
        "annual_rate": annual_rate,
        "monthly_service_fee": monthly_service_fee,
        "repayment_strategy": repayment_strategy,
        "scenario": {
            "global_extra_payment": global_extra_payment,
            "interval_extra_payment": interval_extra_payment,
            "interval_months": interval_months,
            "one_time_payments": one_time_payments,
            "monthly_extras": monthly_extras,
        },
    }


def parse_number(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise LoanValidationError(f"{label} must be a number.") from None
    if not math.isfinite(number):
        raise LoanValidationError(f"{label} must be a finite number.")
    return number


def parse_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise LoanValidationError(f"{label} must be a whole number.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise LoanValidationError(f"{label} must be a whole number.") from None
    return number


def value_is_present(value: Any) -> bool:
    return value is not None and value != ""


def resolve_pricing(request: dict[str, Any]) -> dict[str, object]:
    annual_rate = request.get("annual_rate")
    if annual_rate is not None:
        return {
            "pricing_method": "manual_rate",
            "base_rate": None,
            "risk_premium": None,
            "total_annual_rate": round(annual_rate, 2),
            "tier": None,
            "risk_category": None,
            "score_range": None,
            "manual_rate": round(annual_rate, 2),
        }

    credit_score = request["credit_score"]
    for tier in PRICING_TIERS:
        if tier.score_min <= credit_score <= tier.score_max:
            total_annual_rate = round(BASE_RATE + tier.risk_premium, 2)
            return {
                "pricing_method": "credit_score",
                "base_rate": BASE_RATE,
                "risk_premium": tier.risk_premium,
                "total_annual_rate": total_annual_rate,
                "tier": tier.tier,
                "risk_category": tier.risk_category,
                "score_range": tier.score_range,
                "manual_rate": None,
            }
    raise LoanValidationError("Unsupported credit score.")


def build_monthly_extras(request: dict[str, Any]) -> dict[int, float]:
    extras = {month: 0.0 for month in range(1, request["term_months"] + 1)}
    scenario = request["scenario"]

    for month in extras:
        extras[month] += scenario["global_extra_payment"]
        if scenario["interval_extra_payment"] and month % scenario["interval_months"] == 0:
            extras[month] += scenario["interval_extra_payment"]

    for payment in scenario["one_time_payments"]:
        if payment["month"] in extras:
            extras[payment["month"]] += payment["amount"]

    for month, amount in scenario["monthly_extras"].items():
        if month in extras:
            extras[month] += amount

    return extras


def build_scenario_result(
    *,
    principal: float,
    term_months: int,
    annual_rate: float,
    monthly_service_fee: float,
    repayment_strategy: str,
    scenario: dict[int, float],
) -> dict[str, object]:
    monthly_rate = annual_rate / 100 / 12
    contractual_monthly_payment = calculate_monthly_payment(principal, term_months, monthly_rate)
    current_monthly_payment = contractual_monthly_payment
    scheduled_monthly_outflow = contractual_monthly_payment + monthly_service_fee

    balance = principal
    rows: list[dict[str, object]] = []
    total_paid = 0.0
    total_interest = 0.0
    total_extra_paid = 0.0
    total_service_fees = 0.0

    for month in range(1, term_months + 1):
        opening_balance = balance
        interest_payment = opening_balance * monthly_rate
        scheduled_principal = min(current_monthly_payment - interest_payment, opening_balance)
        scheduled_payment = interest_payment + scheduled_principal

        requested_extra = max(scenario.get(month, 0.0), 0.0)
        max_extra = max(opening_balance - scheduled_principal, 0.0)
        extra_payment = min(requested_extra, max_extra)

        service_fee = monthly_service_fee
        total_payment = scheduled_payment + extra_payment + service_fee
        closing_balance = max(opening_balance - scheduled_principal - extra_payment, 0.0)

        rows.append(
            {
                "month": month,
                "opening_balance": round(opening_balance, 2),
                "scheduled_payment": round(scheduled_payment, 2),
                "service_fee": round(service_fee, 2),
                "interest_payment": round(interest_payment, 2),
                "base_principal_payment": round(scheduled_principal, 2),
                "extra_payment": round(extra_payment, 2),
                "total_payment": round(total_payment, 2),
                "closing_balance": round(closing_balance, 2),
            }
        )

        total_paid += total_payment
        total_interest += interest_payment
        total_extra_paid += extra_payment
        total_service_fees += service_fee
        balance = closing_balance

        if (
            repayment_strategy == "payment_recast"
            and extra_payment > 0
            and balance > EPSILON
            and month < term_months
        ):
            remaining_months = term_months - month
            current_monthly_payment = calculate_monthly_payment(
                balance,
                remaining_months,
                monthly_rate,
            )

        if balance <= EPSILON:
            break

    return {
        "summary": {
            "total_paid": round(total_paid, 2),
            "total_interest": round(total_interest, 2),
            "total_extra_paid": round(total_extra_paid, 2),
            "total_service_fees": round(total_service_fees, 2),
            "actual_term_months": len(rows),
            "monthly_payment": round(contractual_monthly_payment, 2),
            "scheduled_monthly_outflow": round(scheduled_monthly_outflow, 2),
            "monthly_service_fee": round(monthly_service_fee, 2),
            "annual_rate": round(annual_rate, 2),
            "monthly_rate": round(monthly_rate * 100, 4),
        },
        "schedule": rows,
    }


def calculate_monthly_payment(principal: float, term_months: int, monthly_rate: float) -> float:
    if monthly_rate == 0:
        return principal / term_months
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** (-term_months))
