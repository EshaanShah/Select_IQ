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
  prompt: string | null;
  target: number | null;
  analysisStatus: AnalysisStatus;
  analysisTotal: number;
  analysisCompleted: number;
  analysisFailed: number;
  analysisFailures: AnalysisFailure[];
  analysisModel?: string | null;
  analysisCheckpoint?: string | null;
  embeddingDimension?: number | null;
};

export type AnalysisStatus =
  | "idle"
  | "queued"
  | "running"
  | "completed"
  | "partial_failure"
  | "failed";

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

export type PromptTargetResult = {
  projectId: ProjectId;
  prompt: string;
  target: number;
  acceptedCount: number;
};

export type InterpretationStatus = "not_started" | "running" | "completed" | "failed";

export type PhotoNote = {
  photoId: PhotoId;
  originalFilename: string;
  effect: "boost" | "penalize";
  reason: string;
};

export type RankingEntry = {
  photoId: PhotoId;
  originalFilename: string;
  rank: number;
  guidedScore: number | null;
  briefRelevance: number | null;
  explanation: string | null;
};

export type Interpretation = {
  projectId: ProjectId;
  status: InterpretationStatus;
  provider: string | null;
  model: string | null;
  summary: string | null;
  positiveDescriptors: string[];
  negativeDescriptors: string[];
  photoNotes: PhotoNote[];
  errorCode: string | null;
  errorMessage: string | null;
  createdAt?: string | null;
  durationMs?: number | null;
  rankingBasis: "guided" | "brief_relevance";
  ranking: RankingEntry[];
};

export type InterpretationStarted = {
  projectId: ProjectId;
  status: string;
};

export type ProvenanceKind = "ai_informed" | "partial_ai" | "test_signals";

export type ProposalProvenance = {
  kind: ProvenanceKind;
  label: string;
  embeddingModel: string;
  embeddingsGenuine: boolean;
  guidanceModel: string | null;
  guidanceStatus: "completed" | "failed" | "not_started";
  guidanceGenuine: boolean;
  comparisonsUsed: number;
  preferenceMethod: string;
  excludedPhotoCount: number;
};

export type SignalContributions = {
  promptRelevance: number;
  aiGuidance: number;
  preference: number;
};

export type Recommendation = {
  photoId: PhotoId;
  originalFilename: string;
  rank: number;
  score: number;
  contributions: SignalContributions;
  removed: boolean;
};

export type Proposal = {
  proposalId: string;
  projectId: ProjectId;
  version: number;
  targetCount: number;
  selectedCount: number;
  removedCount: number;
  isGenuineAi: boolean;
  provenance: ProposalProvenance;
  parameters: Record<string, unknown>;
  createdAt: string | null;
  recommendations: Recommendation[];
};
