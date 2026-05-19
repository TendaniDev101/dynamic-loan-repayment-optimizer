import { lazy, startTransition, Suspense, useDeferredValue, useEffect, useState } from "react";
import { fetchOptimization } from "./api";
import {
  formatCurrency,
  formatGroupedDecimal,
  formatPercent,
  normalizeDecimalInput,
  sanitizeDecimalInput,
} from "./formatters";

const termOptions = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72];
const ChartSection = lazy(() => import("./ChartSection"));

const initialInputs = {
  principal: 250000,
  monthlyServiceFee: "0.00",
  termMonths: 60,
  repaymentStrategy: "termReduction",
  pricingMode: "creditScore",
  creditScore: 705,
  annualRate: "11.75",
  recurringExtraPayment: 5000,
  recurringFrequencyMonths: 12,
};

const initialOneTimePayments = [{ id: crypto.randomUUID(), month: 24, amount: 8000 }];

export default function App() {
  const [inputs, setInputs] = useState(initialInputs);
  const [oneTimePayments, setOneTimePayments] = useState(initialOneTimePayments);
  const [monthlyExtras, setMonthlyExtras] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const validationErrors = validateForm(inputs, oneTimePayments);
  const hasValidationErrors = Object.keys(validationErrors).length > 0;
  const isManualRateMode = inputs.pricingMode === "manualRate";
  const isPaymentRecastMode = inputs.repaymentStrategy === "paymentRecast";
  const recurringExtraAmount = Number(inputs.recurringExtraPayment) || 0;
  const recurringFrequencyMonths = Number(inputs.recurringFrequencyMonths) || 1;

  const requestPayload = JSON.stringify({
    principal: Number(inputs.principal),
    monthly_service_fee: Number(inputs.monthlyServiceFee) || 0,
    term_months: Number(inputs.termMonths),
    repayment_strategy: isPaymentRecastMode ? "payment_recast" : "term_reduction",
    ...(isManualRateMode
      ? { annual_rate: Number(inputs.annualRate) }
      : { credit_score: Number(inputs.creditScore) }),
    scenario: {
      global_extra_payment: recurringFrequencyMonths === 1 ? recurringExtraAmount : 0,
      interval_extra_payment: recurringFrequencyMonths > 1 ? recurringExtraAmount : 0,
      interval_months: recurringFrequencyMonths,
      one_time_payments: oneTimePayments
        .filter((payment) => Number(payment.amount) > 0)
        .map((payment) => ({
          month: Number(payment.month),
          amount: Number(payment.amount),
        })),
      monthly_extras: Object.fromEntries(
        Object.entries(monthlyExtras)
          .filter(([, amount]) => Number(amount) > 0)
          .map(([month, amount]) => [Number(month), Number(amount)]),
      ),
    },
  });
  const deferredRequestPayload = useDeferredValue(requestPayload);

  useEffect(() => {
    if (hasValidationErrors) {
      setLoading(false);
      setResult(null);
      setError("Please correct the highlighted fields before continuing.");
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      try {
        setLoading(true);
        setError("");
        const response = await fetchOptimization(JSON.parse(deferredRequestPayload));
        startTransition(() => setResult(response));
      } catch (requestError) {
        setError(requestError.message);
      } finally {
        setLoading(false);
      }
    }, 180);

    return () => window.clearTimeout(timeoutId);
  }, [deferredRequestPayload, hasValidationErrors]);

  const optimizedSchedule = result?.optimized.schedule ?? [];
  const baseInstallmentAmount =
    result?.baseline.summary?.scheduled_monthly_outflow ?? null;
  const paymentCompositionData = optimizedSchedule.map((row) => ({
    month: row.month,
    Interest: row.interest_payment,
    BasePrincipal: row.base_principal_payment,
    ServiceFee: row.service_fee,
    ExtraPrincipal: row.extra_payment,
  }));
  const activeRepaymentStrategy =
    result?.repayment_strategy ?? (isPaymentRecastMode ? "payment_recast" : "term_reduction");

  return (
    <div className="app-shell">
      <header className="page-intro">
        <div className="intro-copy-block">
          <h1>Loan Repayment Optimizer</h1>
          <p className="hero-tagline">
            Model your repayment strategy and uncover interest savings early.
          </p>
        </div>
      </header>

      <section className="input-grid">
        <section className="panel-section input-card">
          <h2>Loan Inputs</h2>
          <label>
            Principal
            <FormattedMoneyInput
              invalid={Boolean(validationErrors.principal)}
              value={inputs.principal}
              onChange={(event) =>
                setInputs((current) => ({
                  ...current,
                  principal: event.target.value,
                }))
              }
            />
            <FieldError message={validationErrors.principal} />
          </label>

          <label>
            Monthly Service Fee
            <FormattedMoneyInput
              value={inputs.monthlyServiceFee}
              onChange={(event) =>
                setInputs((current) => ({
                  ...current,
                  monthlyServiceFee: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Repayment Strategy
            <div className="term-input">
              <span className="term-prefix">Mode</span>
              <select
                value={inputs.repaymentStrategy}
                onChange={(event) =>
                  setInputs((current) => ({
                    ...current,
                    repaymentStrategy: event.target.value,
                  }))
                }
              >
                <option value="termReduction">Term Reduction</option>
                <option value="paymentRecast">Lower Installments</option>
              </select>
            </div>
          </label>

          <label>
            Pricing Method
            <div className="term-input">
              <span className="term-prefix">Mode</span>
              <select
                value={inputs.pricingMode}
                onChange={(event) =>
                  setInputs((current) => ({
                    ...current,
                    pricingMode: event.target.value,
                  }))
                }
              >
                <option value="creditScore">Use Credit Score</option>
                <option value="manualRate">Set Interest Rate</option>
              </select>
            </div>
          </label>

          <label>
            Term
            <div className="term-input">
              <span className="term-prefix">Months</span>
              <select
                value={inputs.termMonths}
                onChange={(event) => {
                  const nextTermMonths = Number(event.target.value);

                  setInputs((current) => ({
                    ...current,
                    termMonths: event.target.value,
                    recurringFrequencyMonths: clampWholeNumberInput(
                      current.recurringFrequencyMonths,
                      1,
                      nextTermMonths,
                    ),
                  }));
                  setOneTimePayments((current) =>
                    current.map((entry) => ({
                      ...entry,
                      month: clampWholeNumberInput(entry.month, 1, nextTermMonths),
                    })),
                  );
                }}
              >
                {termOptions.map((term) => (
                  <option key={term} value={term}>
                    {term}
                  </option>
                ))}
              </select>
            </div>
          </label>

          {isManualRateMode ? (
            <label>
              Annual Interest Rate (%)
              <FormattedPercentInput
                invalid={Boolean(validationErrors.annualRate)}
                value={inputs.annualRate}
                onChange={(event) =>
                  setInputs((current) => ({
                    ...current,
                    annualRate: event.target.value,
                  }))
                }
              />
              <FieldError message={validationErrors.annualRate} />
            </label>
          ) : (
            <label>
              Credit Score
              <div className="range-value">{inputs.creditScore}</div>
              <input
                type="range"
                min="300"
                max="850"
                value={inputs.creditScore}
                onChange={(event) =>
                  setInputs((current) => ({
                    ...current,
                    creditScore: event.target.value,
                  }))
                }
              />
            </label>
          )}
        </section>

        <section className="panel-section input-card">
          <h2>Recurring Extra Payments</h2>
          <label>
            <span className="field-label-row">
              <span>
                {activeRepaymentStrategy === "payment_recast"
                  ? "Starting Repayment"
                  : "Base Repayment"}
              </span>
              <span className="readonly-badge">Auto-calculated</span>
            </span>
            <ReadonlyMoneyField
              value={baseInstallmentAmount}
              placeholder="Waiting for loan inputs"
            />
          </label>

          <div className="field-row">
            <label>
              Extra Repayment
              <FormattedMoneyInput
                value={inputs.recurringExtraPayment}
                onChange={(event) =>
                  setInputs((current) => ({
                    ...current,
                    recurringExtraPayment: event.target.value,
                  }))
                }
              />
            </label>

            <label>
              Frequency From Month 1
              <div
                className={`term-input frequency-input ${
                  validationErrors.recurringFrequencyMonths ? "field-invalid" : ""
                }`.trim()}
              >
                <span className="term-prefix">Months</span>
                <input
                  type="number"
                  min="1"
                  max={inputs.termMonths}
                  value={inputs.recurringFrequencyMonths}
                  onChange={(event) =>
                    setInputs((current) => ({
                      ...current,
                      recurringFrequencyMonths: sanitizeWholeNumberInput(event.target.value),
                    }))
                  }
                  onBlur={(event) =>
                    setInputs((current) => ({
                      ...current,
                      recurringFrequencyMonths: clampWholeNumberInput(
                        event.target.value,
                        1,
                        Number(current.termMonths),
                      ),
                    }))
                  }
                  onKeyDown={(event) => {
                    if (event.key !== "Enter") {
                      return;
                    }

                    event.preventDefault();
                    setInputs((current) => ({
                      ...current,
                      recurringFrequencyMonths: clampWholeNumberInput(
                        event.currentTarget.value,
                        1,
                        Number(current.termMonths),
                      ),
                    }));
                    event.currentTarget.blur();
                  }}
                />
              </div>
              <FieldError message={validationErrors.recurringFrequencyMonths} />
            </label>
          </div>
          <p className="field-note">
            {isPaymentRecastMode
              ? "Each extra payment reduces the outstanding balance and recalculates a lower scheduled installment for the remaining original term."
              : "Each extra payment goes straight to principal while keeping the scheduled installment fixed, which shortens the payoff term."}{" "}
            The extra repayment repeats from the first month of the loan, then every{" "}
            {inputs.recurringFrequencyMonths || 1} month
            {Number(inputs.recurringFrequencyMonths || 1) === 1 ? "" : "s"} after that.
          </p>
        </section>

        <section className="panel-section input-card one-time-panel">
          <div className="section-heading">
            <h2>One-Time Payments</h2>
            <button
              type="button"
              className="ghost-button"
              onClick={() =>
                setOneTimePayments((current) => [
                  ...current,
                  { id: crypto.randomUUID(), month: 12, amount: 0 },
                ])
              }
            >
              Add Row
            </button>
          </div>

          <div className="one-time-scroll">
            <div className="mini-grid">
              {oneTimePayments.map((payment) => (
                <div key={payment.id} className="mini-card">
                  <label>
                    Month
                    <div
                      className={`term-input month-input ${
                        validationErrors[`oneTimeMonth:${payment.id}`] ? "field-invalid" : ""
                      }`.trim()}
                    >
                      <span className="term-prefix">Month</span>
                      <input
                        className="aligned-number-input"
                        type="number"
                        min="1"
                        max={inputs.termMonths}
                        value={payment.month}
                        onChange={(event) =>
                          setOneTimePayments((current) =>
                            current.map((entry) =>
                              entry.id === payment.id
                                ? {
                                    ...entry,
                                    month: sanitizeWholeNumberInput(event.target.value),
                                  }
                                : entry,
                            ),
                          )
                        }
                        onBlur={(event) =>
                          setOneTimePayments((current) =>
                            current.map((entry) =>
                              entry.id === payment.id
                                ? {
                                    ...entry,
                                    month: clampWholeNumberInput(
                                      event.target.value,
                                      1,
                                      Number(inputs.termMonths),
                                    ),
                                  }
                                : entry,
                            ),
                          )
                        }
                        onKeyDown={(event) => {
                          if (event.key !== "Enter") {
                            return;
                          }

                          event.preventDefault();
                          setOneTimePayments((current) =>
                            current.map((entry) =>
                              entry.id === payment.id
                                ? {
                                    ...entry,
                                    month: clampWholeNumberInput(
                                      event.currentTarget.value,
                                      1,
                                      Number(inputs.termMonths),
                                    ),
                                  }
                                : entry,
                            ),
                          );
                          event.currentTarget.blur();
                        }}
                      />
                    </div>
                    <FieldError message={validationErrors[`oneTimeMonth:${payment.id}`]} />
                  </label>

                  <label>
                    Amount
                    <FormattedMoneyInput
                      value={payment.amount}
                      onChange={(event) =>
                        setOneTimePayments((current) =>
                          current.map((entry) =>
                            entry.id === payment.id
                              ? { ...entry, amount: event.target.value }
                              : entry,
                          ),
                        )
                      }
                    />
                  </label>

                  <button
                    type="button"
                    className="text-button danger-button"
                    onClick={() =>
                      setOneTimePayments((current) =>
                        current.filter((entry) => entry.id !== payment.id),
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>
      </section>

      <main className="dashboard">
        <section className="hero-card">
          <div>
            <p className="eyebrow">Pricing Snapshot</p>
            <h2>
              {result
                ? result.pricing.pricing_method === "manual_rate"
                  ? `Manual rate at ${formatPercent(result.pricing.total_annual_rate)} APR`
                  : `${result.pricing.tier} at ${formatPercent(result.pricing.total_annual_rate)} APR`
                : "Loading pricing model"}
            </h2>
            <p className="hero-copy">
              {result
                ? result.pricing.pricing_method === "manual_rate"
                  ? `Annual interest rate entered directly at ${formatPercent(
                      result.pricing.manual_rate,
                    )}, without using credit-score pricing.`
                  : `Base rate ${formatPercent(result.pricing.base_rate)} plus risk premium ${formatPercent(
                      result.pricing.risk_premium,
                    )} for scores in ${result.pricing.score_range}.`
                : "Loading pricing details."}
            </p>
          </div>
          <div className="hero-metric">
            <span>
              {activeRepaymentStrategy === "payment_recast"
                ? "Original payoff term"
                : "Optimized payoff"}
            </span>
            <strong>
              {result ? `${result.optimized.summary.actual_term_months} months` : "--"}
            </strong>
          </div>
        </section>

        <section className="disclaimer-card" aria-label="Calculator disclaimer">
          <p className="eyebrow">Important Disclaimer</p>
          <p>
            This calculator models loan repayment using principal, interest rate, term,
            monthly service fees, and extra payments. It does not include initiation
            fees, insurance premiums, penalties, taxes, or any other lender charges
            that may apply to the money borrowed.
          </p>
        </section>

        <section className="kpi-grid">
          <MetricCard
            label="Total Paid"
            baseline={result?.baseline.summary.total_paid}
            optimized={result?.optimized.summary.total_paid}
            gain={result?.deltas.total_paid_saved}
          />
          <MetricCard
            label="Interest Paid"
            baseline={result?.baseline.summary.total_interest}
            optimized={result?.optimized.summary.total_interest}
            gain={result?.deltas.total_interest_saved}
          />
          <MetricCard
            label="Service Fees"
            baseline={result?.baseline.summary.total_service_fees}
            optimized={result?.optimized.summary.total_service_fees}
            gain={
              result
                ? result.baseline.summary.total_service_fees -
                  result.optimized.summary.total_service_fees
                : null
            }
          />
          <MetricCard
            label={
              activeRepaymentStrategy === "payment_recast"
                ? "Payoff Term"
                : "Time To Zero Debt"
            }
            baseline={result?.baseline.summary.actual_term_months}
            optimized={result?.optimized.summary.actual_term_months}
            gain={
              activeRepaymentStrategy === "payment_recast"
                ? null
                : result?.deltas.months_saved
            }
            formatValue={(value) => `${value} months`}
          />
        </section>

        {error ? <div className="status-card error">{error}</div> : null}
        {loading ? <div className="status-card">Refreshing scenario...</div> : null}

        <Suspense fallback={<div className="status-card">Loading charts...</div>}>
          <ChartSection
            result={result}
            paymentCompositionData={paymentCompositionData}
          />
        </Suspense>

        <section className="table-card">
          <div className="card-heading">
            <h3>Interactive Amortization Schedule</h3>
            <p>Edit month-specific extra payments.</p>
          </div>

          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Opening</th>
                  <th>Repayment</th>
                  <th>Service Fee</th>
                  <th>Interest</th>
                  <th>Base Principal</th>
                  <th>Extra Payment</th>
                  <th>Total Paid</th>
                  <th>Closing</th>
                </tr>
              </thead>
              <tbody>
                {optimizedSchedule.map((row) => (
                  <tr key={row.month}>
                    <td>{row.month}</td>
                    <td>{formatCurrency(row.opening_balance)}</td>
                    <td>{formatCurrency(row.scheduled_payment)}</td>
                    <td>{formatCurrency(row.service_fee)}</td>
                    <td>{formatCurrency(row.interest_payment)}</td>
                    <td>{formatCurrency(row.base_principal_payment)}</td>
                    <td>
                      <FormattedMoneyInput
                        className="table-input"
                        value={monthlyExtras[row.month] ?? ""}
                        placeholder={formatGroupedDecimal(row.extra_payment)}
                        onChange={(event) =>
                          setMonthlyExtras((current) => ({
                            ...current,
                            [row.month]: event.target.value,
                          }))
                        }
                      />
                    </td>
                    <td>{formatCurrency(row.total_payment)}</td>
                    <td>{formatCurrency(row.closing_balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

function MetricCard({ label, baseline, optimized, gain, formatValue = formatCurrency }) {
  return (
    <article className="metric-card">
      <p>{label}</p>
      <strong>{optimized != null ? formatValue(optimized) : "--"}</strong>
      <div className="metric-meta">
        <span>Baseline {baseline != null ? formatValue(baseline) : "--"}</span>
        <span>Savings {gain != null ? formatValue(gain) : "--"}</span>
      </div>
    </article>
  );
}

function FormattedMoneyInput({
  value,
  onChange,
  className = "",
  placeholder = "",
  invalid = false,
}) {
  const [isFocused, setIsFocused] = useState(false);

  const commitValue = (nextValue) => {
    onChange({ target: { value: normalizeDecimalInput(nextValue) } });
    setIsFocused(false);
  };

  const displayValue = isFocused
    ? String(value ?? "")
    : formatGroupedDecimal(normalizeDecimalInput(String(value ?? "")));

  return (
    <div className={`currency-input ${invalid ? "field-invalid" : ""} ${className}`.trim()}>
      <span className="currency-prefix">ZAR</span>
      <input
        type="text"
        inputMode="decimal"
        value={displayValue}
        placeholder={placeholder}
        onFocus={() => setIsFocused(true)}
        onBlur={(event) => commitValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key !== "Enter") {
            return;
          }

          event.preventDefault();
          commitValue(event.currentTarget.value);
          event.currentTarget.blur();
        }}
        onChange={(event) => {
          onChange({
            target: { value: sanitizeDecimalInput(event.target.value) },
          });
        }}
      />
    </div>
  );
}

function FieldError({ message }) {
  if (!message) {
    return null;
  }

  return <span className="field-error">{message}</span>;
}

function FormattedPercentInput({
  value,
  onChange,
  className = "",
  placeholder = "",
  invalid = false,
}) {
  const [isFocused, setIsFocused] = useState(false);

  const commitValue = (nextValue) => {
    onChange({ target: { value: normalizeDecimalInput(nextValue) } });
    setIsFocused(false);
  };

  const displayValue = isFocused
    ? String(value ?? "")
    : formatGroupedDecimal(normalizeDecimalInput(String(value ?? "")));

  return (
    <div className={`currency-input ${invalid ? "field-invalid" : ""} ${className}`.trim()}>
      <span className="currency-prefix">APR</span>
      <input
        type="text"
        inputMode="decimal"
        value={displayValue}
        placeholder={placeholder}
        onFocus={() => setIsFocused(true)}
        onBlur={(event) => commitValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key !== "Enter") {
            return;
          }

          event.preventDefault();
          commitValue(event.currentTarget.value);
          event.currentTarget.blur();
        }}
        onChange={(event) => {
          onChange({
            target: { value: sanitizeDecimalInput(event.target.value) },
          });
        }}
      />
    </div>
  );
}

function ReadonlyMoneyField({ value, placeholder = "--", className = "" }) {
  const displayValue = value == null ? placeholder : formatGroupedDecimal(value);

  return (
    <div className={`currency-input static-field ${className}`.trim()}>
      <span className="currency-prefix">ZAR</span>
      <span className="static-field-value">{displayValue}</span>
    </div>
  );
}

function validateForm(inputs, oneTimePayments) {
  const errors = {};
  const principalValue = Number(inputs.principal);
  if (!inputs.principal || Number.isNaN(principalValue) || principalValue <= 0) {
    errors.principal = "Enter a principal greater than 0.";
  }

  const frequencyValue = Number(inputs.recurringFrequencyMonths);
  if (
    !inputs.recurringFrequencyMonths ||
    Number.isNaN(frequencyValue) ||
    frequencyValue < 1 ||
    frequencyValue > Number(inputs.termMonths)
  ) {
    errors.recurringFrequencyMonths = `Enter a value between 1 and ${inputs.termMonths}.`;
  }

  if (inputs.pricingMode === "manualRate") {
    const annualRateValue = Number(inputs.annualRate);
    if (inputs.annualRate === "" || Number.isNaN(annualRateValue) || annualRateValue < 0) {
      errors.annualRate = "Enter an annual interest rate of 0 or greater.";
    }
  }

  for (const payment of oneTimePayments) {
    const paymentMonth = Number(payment.month);
    if (!payment.month || Number.isNaN(paymentMonth)) {
      errors[`oneTimeMonth:${payment.id}`] = "Enter a valid month number.";
      continue;
    }

    if (paymentMonth < 1 || paymentMonth > Number(inputs.termMonths)) {
      errors[`oneTimeMonth:${payment.id}`] = `Use a month between 1 and ${inputs.termMonths}.`;
    }
  }

  return errors;
}

function sanitizeWholeNumberInput(value) {
  return value.replace(/\D/g, "");
}

function clampWholeNumberInput(value, min, max) {
  const sanitizedValue = sanitizeWholeNumberInput(String(value ?? ""));
  if (!sanitizedValue) {
    return String(min);
  }

  const numericValue = Number(sanitizedValue);
  if (Number.isNaN(numericValue)) {
    return String(min);
  }

  return String(Math.min(max, Math.max(min, Math.trunc(numericValue))));
}
