export type ProjectId = string;
export type PhotoId = string;

export type ProcessingState = "pending" | "processing" | "completed" | "failed";

export type ImportFailure = {
  filename: string;
  code: string;
  message: string;
  createdAt?: string | null;
};

export type ProjectCreated = {
  projectId: ProjectId;
  acceptedCount: number;
};

export type AcceptedPhoto = {
  photoId: PhotoId;
  originalFilename: string;
  width: number;
  height: number;
  byteSize: number;
  state: ProcessingState;
};

export type ImportResult = {
  accepted: AcceptedPhoto[];
  rejected: ImportFailure[];
  batchAcceptedCount: number;
  batchRejectedCount: number;
  acceptedCount: number;
};

export type ProjectStatus = {
  projectId: ProjectId;
  acceptedCount: number;
  remainingCapacity: number;
  failures: ImportFailure[];
  analysisStatus: AnalysisStatus;
  analysisTotal: number;
  analysisCompleted: number;
  analysisFailed: number;
  analysisFailures: AnalysisFailure[];
  analysisModel?: string | null;
  analysisCheckpoint?: string | null;
  embeddingDimension?: number | null;
};

export type AnalysisStatus = "idle" | "queued" | "running" | "completed" | "partial_failure" | "failed";

export type AnalysisFailure = {
  photoId: PhotoId;
  originalFilename: string;
  code: string;
  message: string;
};

export type AnalysisStarted = {
  projectId: ProjectId;
  analysisStatus: AnalysisStatus;
};
