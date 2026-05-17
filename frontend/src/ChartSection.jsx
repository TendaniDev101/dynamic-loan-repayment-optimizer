import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "./formatters";

export default function ChartSection({ result, paymentCompositionData }) {
  const lineChartData = buildLineChartData(result);

  return (
    <section className="chart-grid">
      <article className="chart-card">
        <div className="card-heading">
          <h3>Remaining Balance Trajectory</h3>
          <p>Baseline vs optimized path to zero.</p>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={lineChartData}>
            <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="month" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" tickFormatter={formatCompactCurrency} />
            <Tooltip
              formatter={(value) => formatCurrency(value)}
              contentStyle={tooltipStyle}
            />
            <Line
              type="monotone"
              dataKey="Baseline"
              stroke="#f59e0b"
              strokeWidth={3}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="Optimized"
              stroke="#34d399"
              strokeWidth={3}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </article>

      <article className="chart-card">
        <div className="card-heading">
          <h3>Payment Composition</h3>
          <p>How interest, base principal, and extra principal evolve each month.</p>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={paymentCompositionData}>
            <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="month" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" tickFormatter={formatCompactCurrency} />
            <Tooltip
              formatter={(value) => formatCurrency(value)}
              contentStyle={tooltipStyle}
            />
            <Bar dataKey="Interest" stackId="payment" fill="#fb7185" />
            <Bar dataKey="BasePrincipal" stackId="payment" fill="#60a5fa" />
            <Bar dataKey="ExtraPrincipal" stackId="payment" fill="#22c55e" />
          </BarChart>
        </ResponsiveContainer>
      </article>
    </section>
  );
}

function buildLineChartData(result) {
  if (!result) {
    return [];
  }

  const maxLength = Math.max(
    result.baseline.schedule.length,
    result.optimized.schedule.length,
  );

  return Array.from({ length: maxLength }, (_, index) => {
    const baselineRow = result.baseline.schedule[index];
    const optimizedRow = result.optimized.schedule[index];

    return {
      month: index + 1,
      Baseline: baselineRow?.closing_balance ?? 0,
      Optimized: optimizedRow?.closing_balance ?? 0,
    };
  });
}

function formatCompactCurrency(value) {
  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

const tooltipStyle = {
  backgroundColor: "#09111f",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  borderRadius: "16px",
};

