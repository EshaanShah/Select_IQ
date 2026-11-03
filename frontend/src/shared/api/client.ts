import type {
  AnalysisStarted,
  ImportResult,
  ProjectCreated,
  ProjectStatus,
  PromptTargetResult,
} from "../types";

const apiBaseUrl = import.meta.env.VITE_SELECTIQ_API_URL ?? "http://localhost:8000";

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);

  if (!response.ok) {
    let detail = `SelectIQ API request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // The fallback includes the status when an upstream response is not JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function createProject(): Promise<ProjectCreated> {
  return apiRequest<ProjectCreated>("/projects", { method: "POST" });
}

export function getProjectStatus(projectId: string): Promise<ProjectStatus> {
  return apiRequest<ProjectStatus>(`/projects/${projectId}/status`);
}

export function uploadPhotos(projectId: string, files: File[]): Promise<ImportResult> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file, file.name));
  return apiRequest<ImportResult>(`/projects/${projectId}/photos`, {
    method: "POST",
    body: formData,
  });
}

export function savePromptAndTarget(
  projectId: string,
  prompt: string,
  target: number,
): Promise<PromptTargetResult> {
  return apiRequest<PromptTargetResult>(`/projects/${projectId}/brief`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, target }),
  });
}

export function startAnalysis(projectId: string): Promise<AnalysisStarted> {
  return apiRequest<AnalysisStarted>(`/projects/${projectId}/analyze`, { method: "POST" });
}
