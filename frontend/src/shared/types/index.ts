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
};
