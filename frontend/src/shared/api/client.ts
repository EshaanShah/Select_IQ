import type {
  AnalysisStarted,
  ImportResult,
  Interpretation,
  InterpretationStarted,
  ProjectCreated,
  ProjectStatus,
  PromptTargetResult,
  Proposal,
} from "../types";

const apiBaseUrl = import.meta.env.VITE_SELECTIQ_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);

  if (!response.ok) {
    let detail = `SelectIQ API request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // The fallback includes the status when an upstream response is not JSON.
    }
    throw new ApiError(detail, response.status);
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

export function getInterpretation(projectId: string): Promise<Interpretation> {
  return apiRequest<Interpretation>(`/projects/${projectId}/interpretation`);
}

export function startInterpretation(projectId: string): Promise<InterpretationStarted> {
  return apiRequest<InterpretationStarted>(`/projects/${projectId}/interpretation`, {
    method: "POST",
  });
}

export async function getProposal(projectId: string): Promise<Proposal | null> {
  try {
    return await apiRequest<Proposal>(`/projects/${projectId}/recommendations`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export function generateProposal(projectId: string): Promise<Proposal> {
  return apiRequest<Proposal>(`/projects/${projectId}/recommendations`, { method: "POST" });
}

export function removeFromSelection(projectId: string, photoId: string): Promise<Proposal> {
  return apiRequest<Proposal>(`/projects/${projectId}/recommendations/selection/${photoId}`, {
    method: "DELETE",
  });
}

export function restoreToSelection(projectId: string, photoId: string): Promise<Proposal> {
  return apiRequest<Proposal>(
    `/projects/${projectId}/recommendations/selection/${photoId}/restore`,
    { method: "POST" },
  );
}

export function exportUrl(projectId: string): string {
  return `${apiBaseUrl}/projects/${projectId}/recommendations/export`;
}

export function thumbnailUrl(projectId: string, photoId: string): string {
  return `${apiBaseUrl}/projects/${projectId}/photos/${photoId}/thumbnail`;
}
