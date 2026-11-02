const apiBaseUrl = import.meta.env.VITE_SELECTIQ_API_URL ?? "http://localhost:8000";

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);

  if (!response.ok) {
    throw new Error(`SelectIQ API request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

