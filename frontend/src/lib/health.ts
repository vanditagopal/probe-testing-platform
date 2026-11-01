const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

export const API_BASE_URL = (configuredBaseUrl || "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);

export interface HealthResponse {
  status: "healthy";
}

export async function getBackendHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, { signal });
  if (!response.ok) {
    throw new Error(`Backend health check returned HTTP ${response.status}.`);
  }

  const body: unknown = await response.json();
  if (
    typeof body !== "object" ||
    body === null ||
    !("status" in body) ||
    body.status !== "healthy"
  ) {
    throw new Error("Backend health check returned an unexpected response.");
  }

  return { status: "healthy" };
}
