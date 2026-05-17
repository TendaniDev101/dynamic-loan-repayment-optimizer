const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchOptimization(payload) {
  const response = await fetch(`${API_BASE_URL}/api/optimize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => null);
    const detail =
      typeof errorPayload?.detail === "string"
        ? errorPayload.detail
        : Array.isArray(errorPayload?.detail)
          ? errorPayload.detail.map((entry) => entry.msg).join(" ")
          : null;

    throw new Error(detail || "Failed to calculate optimization scenario.");
  }

  return response.json();
}
