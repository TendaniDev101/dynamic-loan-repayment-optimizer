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


if __name__ == "__main__":
    unittest.main()
