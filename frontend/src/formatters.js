export function formatCurrency(value) {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return "R --";
  }

  return `R ${formatDecimalDisplay(numericValue)}`;
}

export function formatGroupedDecimal(value) {
  if (value === "" || value == null) {
    return "";
  }

  const numericValue = Number(normalizeDecimalSeparators(String(value)));
  if (Number.isNaN(numericValue)) {
    return String(value);
  }

  return formatDecimalDisplay(numericValue);
}

export function sanitizeDecimalInput(value) {
  const cleanedValue = value.replace(",", ".").replace(/[^\d.]/g, "");
  const [wholePart = "", ...decimalParts] = cleanedValue.split(".");

  if (decimalParts.length === 0) {
    return wholePart;
  }

  return `${wholePart}.${decimalParts.join("")}`;
}

export function normalizeDecimalInput(value) {
  if (value === "") {
    return "";
  }

  const numericValue = Number(normalizeDecimalSeparators(String(value)));
  if (Number.isNaN(numericValue)) {
    return "";
  }

  return numericValue.toFixed(2);
}

export function formatPercent(value) {
  return `${value.toFixed(2)}%`;
}

function formatDecimalDisplay(value) {
  return new Intl.NumberFormat("sv-SE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
    .format(value)
    .replace(/\s+/g, " ");
}

function normalizeDecimalSeparators(value) {
  return value.replace(/\s+/g, "").replace(",", ".");
}
