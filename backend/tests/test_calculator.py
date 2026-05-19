import unittest

from backend.app.calculator import build_monthly_extras, optimize_loan
from backend.app.models import LoanRequest, OneTimePayment, ScenarioInput
from pydantic import ValidationError


class CalculatorTests(unittest.TestCase):
    def test_optimizer_shortens_term_with_extra_payments(self) -> None:
        request = LoanRequest(
            principal=100000,
            term_months=60,
            credit_score=700,
            scenario=ScenarioInput(
                global_extra_payment=500,
                interval_extra_payment=2000,
                interval_months=12,
                one_time_payments=[OneTimePayment(month=24, amount=3000)],
            ),
        )

        result = optimize_loan(request)

        self.assertLess(
            result.optimized.summary.actual_term_months,
            result.baseline.summary.actual_term_months,
        )
        self.assertGreater(result.deltas.total_interest_saved, 0)

    def test_optimizer_supports_manual_annual_rate(self) -> None:
        request = LoanRequest(
            principal=100000,
            term_months=60,
            annual_rate=12.5,
            scenario=ScenarioInput(global_extra_payment=500),
        )

        result = optimize_loan(request)

        self.assertEqual(result.pricing.pricing_method, "manual_rate")
        self.assertEqual(result.pricing.total_annual_rate, 12.5)
        self.assertIsNone(result.pricing.tier)
        self.assertGreater(result.deltas.total_interest_saved, 0)

    def test_payment_recast_keeps_term_but_reduces_future_installments(self) -> None:
        request = LoanRequest(
            principal=100000,
            term_months=60,
            credit_score=700,
            repayment_strategy="payment_recast",
            scenario=ScenarioInput(
                one_time_payments=[OneTimePayment(month=12, amount=5000)],
            ),
        )

        result = optimize_loan(request)

        self.assertEqual(result.repayment_strategy, "payment_recast")
        self.assertEqual(
            result.optimized.summary.actual_term_months,
            result.baseline.summary.actual_term_months,
        )
        self.assertEqual(result.deltas.months_saved, 0)
        self.assertLess(
            result.optimized.schedule[12].scheduled_payment,
            result.baseline.schedule[12].scheduled_payment,
        )
        self.assertGreater(result.deltas.total_interest_saved, 0)

    def test_monthly_service_fee_increases_total_paid_without_changing_interest(self) -> None:
        base_request = LoanRequest(
            principal=50000,
            term_months=12,
            credit_score=760,
        )
        fee_request = LoanRequest(
            principal=50000,
            term_months=12,
            credit_score=760,
            monthly_service_fee=69,
        )

        base_result = optimize_loan(base_request)
        fee_result = optimize_loan(fee_request)

        self.assertEqual(
            fee_result.baseline.summary.actual_term_months,
            base_result.baseline.summary.actual_term_months,
        )
        self.assertEqual(
            fee_result.baseline.summary.total_interest,
            base_result.baseline.summary.total_interest,
        )
        self.assertEqual(fee_result.baseline.summary.total_service_fees, 828)
        self.assertEqual(
            round(
                fee_result.baseline.summary.total_paid
                - base_result.baseline.summary.total_paid,
                2,
            ),
            828,
        )
        self.assertEqual(
            round(
                fee_result.baseline.summary.scheduled_monthly_outflow
                - base_result.baseline.summary.scheduled_monthly_outflow,
                2,
            ),
            69,
        )

    def test_extra_schedule_combines_rule_types(self) -> None:
        request = LoanRequest(
            principal=50000,
            term_months=12,
            credit_score=760,
            scenario=ScenarioInput(
                global_extra_payment=100,
                interval_extra_payment=500,
                interval_months=6,
                one_time_payments=[OneTimePayment(month=6, amount=250)],
                monthly_extras={6: 50},
            ),
        )

        extras = build_monthly_extras(request)

        self.assertEqual(extras[1], 100)
        self.assertEqual(extras[6], 900)

    def test_validation_rejects_one_time_payment_beyond_term(self) -> None:
        with self.assertRaises(ValidationError):
            LoanRequest(
                principal=50000,
                term_months=12,
                credit_score=760,
                scenario=ScenarioInput(
                    one_time_payments=[OneTimePayment(month=18, amount=250)],
                ),
            )

    def test_validation_rejects_negative_monthly_extra_amount(self) -> None:
        with self.assertRaises(ValidationError):
            LoanRequest(
                principal=50000,
                term_months=12,
                credit_score=760,
                scenario=ScenarioInput(monthly_extras={6: -50}),
            )

    def test_validation_rejects_frequency_beyond_term(self) -> None:
        with self.assertRaises(ValidationError):
            LoanRequest(
                principal=50000,
                term_months=12,
                credit_score=760,
                scenario=ScenarioInput(interval_months=24),
            )

    def test_validation_requires_one_pricing_input(self) -> None:
        with self.assertRaises(ValidationError):
            LoanRequest(
                principal=50000,
                term_months=12,
            )

    def test_validation_rejects_both_pricing_inputs(self) -> None:
        with self.assertRaises(ValidationError):
            LoanRequest(
                principal=50000,
                term_months=12,
                credit_score=760,
                annual_rate=11.5,
            )


if __name__ == "__main__":
    unittest.main()
