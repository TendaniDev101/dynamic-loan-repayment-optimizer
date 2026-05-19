# The Math

## Scope

This note explains the two repayment strategies implemented in this calculator:

- `term_reduction`
- `payment_recast`

The focus here is the amortization math.

## Common Loan Equations

Let:

- `PV` = original principal
- `n` = original loan term in months
- `i_ann` = annual interest rate as a percentage
- `r` = monthly interest rate in decimal form

Then:

$$
r = \frac{i_{ann}}{12 \times 100}
$$

The standard monthly installment for a fully amortizing loan is:

$$
P_0 = \frac{PV \cdot r}{1 - (1+r)^{-n}}
$$

For each month `t`:

- `B_open_t` = opening balance
- `I_t` = interest charged that month
- `Pr_t` = scheduled principal paid that month
- `Ex_t` = extra payment made that month
- `P_t` = scheduled installment active for that month
- `B_close_t` = closing balance

Monthly interest is:

$$
I_t = B_{open,t} \cdot r
$$

Scheduled principal is:

$$
Pr_t = P_t - I_t
$$

Closing balance is:

$$
B_{close,t} = B_{open,t} - Pr_t - Ex_t
$$

If a monthly service fee applies, it affects cash outflow but does not reduce principal:

$$
\text{Total Payment}_t = P_t + Ex_t + Fee_t
$$

## Strategy 1: Term Reduction

This is the "pay off faster" strategy.

### Rule

The scheduled installment does not change after extra payments:

$$
P_t = P_0 \quad \text{for all } t
$$

### Monthly Mechanics

Each month:

$$
I_t = B_{open,t} \cdot r
$$

$$
Pr_t = P_0 - I_t
$$

$$
B_{close,t} = B_{open,t} - Pr_t - Ex_t
$$

### Effect

Because extra payments reduce the balance immediately, future interest becomes smaller:

$$
I_{t+1} = B_{close,t} \cdot r
$$

The installment stays fixed, so the loan ends earlier than originally planned. The process stops once:

$$
B_{close,t} \le 0
$$

### Interpretation

This strategy converts extra payments into term savings. The monthly contractual installment remains the same, but the maturity date moves forward.

## Strategy 2: Payment Recast / Re-amortization

This is the "lower my monthly payment" strategy.

### Rule

When an extra payment is made, the balance is reduced immediately. Instead of keeping the old installment, the remaining balance is re-amortized over the remaining original term.

For the month in which the extra payment occurs, the currently active installment is still used:

$$
I_t = B_{open,t} \cdot r
$$

$$
Pr_t = P_t - I_t
$$

$$
B_{close,t} = B_{open,t} - Pr_t - Ex_t
$$

If there are remaining months, the next installment is recalculated as:

$$
P_{new} = \frac{B_{close,t} \cdot r}{1 - (1+r)^{-(n-t)}}
$$

where:

$$
\text{remaining months} = n - t
$$

That new installment becomes the scheduled payment for the next month:

$$
P_{t+1} = P_{new}
$$

### Effect

The balance still drops because of the extra payment, and total interest still falls because future interest is charged on a lower outstanding balance. But instead of shortening the term, the loan keeps the original maturity and the installment becomes smaller.

### Interpretation

This strategy converts extra payments into installment relief rather than term savings.

## Key Difference

The difference between the two strategies is entirely in how the installment evolves after an extra payment.

### Term Reduction

$$
P_t = P_0
$$

Extra payments reduce balance and shorten the payoff period.

### Payment Recast

$$
P_{t+1} = \frac{B_{close,t} \cdot r}{1 - (1+r)^{-(n-t)}}
$$

Extra payments reduce balance and trigger a new installment calculation for the remaining original term.

## Conclusion

Mathematically:

- **Term reduction** keeps the installment fixed and allows the term to shrink.
- **Payment recast** keeps the term fixed and allows the installment to shrink.

That is the core distinction implemented in this calculator.
