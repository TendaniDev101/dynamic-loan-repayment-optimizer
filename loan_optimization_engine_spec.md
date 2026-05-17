# Product Specification: Dynamic Loan Optimization Engine & Scenario Planner

## 1. Product Overview
The **Dynamic Loan Optimization Engine** is an interactive web-based financial planning application. Unlike traditional static calculators, this engine evaluates a user's credit profile to dynamically calculate a personalized interest rate using **Risk-Based Pricing**. It simulates an amortization schedule and allows users to stress-test arbitrary repayment scenarios (e.g., recurring monthly overpayments, seasonal lump sums, or periodic adjustments) to instantly visualize timeline reduction and lifetime interest savings.

---

## 2. System Architecture & Core Flow

```
[User Inputs: Amount, Term, Credit Score]
                │
                ▼
   [Risk-Based Pricing Engine] ──► Evaluates Risk Premium & Outputs Final Rate
                │
                ▼
   [Amortization Schedule Engine] ──► Computes Core Base Monthly Payment (PMT)
                │
                ▼
 [Interactive Scenario Layer] ──► Injects Ad-hoc Overpayments & Calculates Term/Interest Savings
                │
                ▼
   [Dynamic Charting & Analytics UI] ──► Renders Visual Amortization & Lifecycle Data
```

---

## 3. Core Features & Functional Requirements

### 3.1. User Input Layer
The application UI must collect three mandatory parameters from the user to initialize the lifecycle engine:
* **Loan Principal Amount ($PV$):** Numeric input representing the total borrowed amount (e.g., ZAR 50,000).
* **Loan Term ($n$):** Select/Dropdown or Slider representing the lifecycle duration in months (e.g., 12, 24, 36, 48, 60 months).
* **Credit Score / Tier:** A slider (300 to 850) or categorical dropdown representing credit risk rating bands (e.g., AAA, A, BB).

### 3.2. Under-the-Hood Actuarial Pricing Engine
The system will run a risk-adjusted lookup matrix to simulate commercial banking rate assembly:
* **Base Rate Floor:** Hardcoded baseline funding and operations index (e.g., Bank Cost of Funds + Profit Margin = 9.75%).
* **Risk-Premium Allocation:** The application maps the user's credit score input into a defined risk category using a backend lookup matrix to append the calculated Risk Premium:

| Credit Tier | Score Range | Risk Category | Risk Premium Appended | Total Annual Customer Rate ($i_{ann}$) |
| :--- | :--- | :--- | :--- | :--- |
| **AAA / Exceptional** | 750 - 850 | Minimum Risk | +0.50% | 10.25% |
| **A / Good** | 680 - 749 | Moderate Risk | +2.00% | 11.75% |
| **BB / Below Average**| 580 - 619 | Elevated Risk | +5.50% | 15.25% |

### 3.3. Core Financial Calculators
The backend execution layer must translate annual parameters into periodic components and compile the base amortization matrix:
* **Monthly Interest Rate ($r$):** Derived dynamically from the assigned annual customer rate: 
    $$r = \frac{i_{ann}}{12}$$
* **Base Monthly Payment ($P$):** Programmatically evaluates the definitive ordinary annuity equation:
    $$P = \frac{PV \times r}{1 - (1 + r)^{-n}}$$

### 3.4. Interactive Scenario Planner (The Amortization Engine)
The web application must build an editable row evaluation matrix up to the maximum term. Every row (representing a month) must expose an interactive input field for **Extra Payments**. The data processing loop evaluates cash flows sequentially:

1. **Opening Balance ($B_{open}$):** For Month 1, evaluates to $PV$. For all subsequent months:
    $$B_{open, \text{ Month } t} = B_{close, \text{ Month } t-1}$$
2. **Interest Component ($I_t$):** Computed directly against current periodic outstanding liability:
    $$I_t = B_{open, t} \times r$$
3. **Base Principal Allocation ($Pr_t$):** Evaluates base allocation before overpayments:
    $$Pr_t = P - I_t$$
4. **Extra Payment Layer ($Ex_t$):** User-defined inline numeric variable mapped to that specific month. Defaults to `0`. User can configure:
    * *Global Rules:* Appends $+X$ to all rows.
    * *Interval Rules:* Appends $+X$ every 6th row (bi-annual bonus injection).
    * *Isolated Instances:* Appends $+X$ explicitly to Month 12 only.
5. **Total Principal Deduction ($Pr_{total}$):**
    $$Pr_{total} = Pr_t + Ex_t$$
6. **Closing Balance ($B_{close}$):** Evaluates the terminal lifecycle value of the period:
    $$B_{close, t} = B_{open, t} - Pr_{total}$$
7. **Termination Break Condition:** If $B_{close, t} \le 0$, the calculation array terminates instantly, discarding all downstream rows. The engine flags index $t$ as the **Actual Repayment Term**.

---

## 4. Front-End User Interface & Data Visualization

### 4.1. The Executive Dashboard (KPI Summaries)
When a scenario is modified, the interface must instantly contrast the baseline model vs. the optimized scenario via a real-time KPI card layout:

| Metric Indicator | Baseline Strategy | Optimized Scenario | Net Efficiency Gain |
| :--- | :--- | :--- | :--- |
| **Total Debt Repaid** | Calculated Cumulative Outflow | New Shortened Cash Outflow | Absolute Capital Saved |
| **Total Interest Forfeited** | Cumulative Base Interest | New Compressed Interest Array | Total Cost of Credit Avoided |
| **Time to Zero Debt** | Original Term Length (e.g., 60M) | Actual Repayment Term Index | Total Months Reclaimed |

### 4.2. Charting Layer
The frontend data visualizations will update in real time as the user types overpayment entries:
* **Amortization Curve Line Chart:** A clear dual-line chart visualizing the downward path of the Remaining Principal over the loan lifecycle. One line maps the slow baseline trajectory; the second line visually demonstrates the accelerated descent to zero triggered by user overpayments.
* **Monthly Payment Composition Stacked Bar Chart:** A vertical stacked bar chart charting months 1 through $n$. Each bar splits the fixed installment into its internal components (Interest Paid vs. Base Principal Paid vs. Extra Principal Paid). It visually demonstrates to the user how interest shrinks over time while the principal repayment components grow.

---

## 5. Technical Stack Recommendations
* **Frontend UI Engine:** React.js or Vue.js (for reactive state management—ensuring that typing an extra payment instantly updates the entire table and chart without a page refresh).
* **Data Visualization UI:** Chart.js, Recharts, or ApexCharts (optimized for rendering seamless stacked bar structures and linear regression paths).
* **Styles Layout:** Tailwind CSS for a highly responsive, clean mobile/desktop interface.
