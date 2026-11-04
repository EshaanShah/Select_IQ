import type { Proposal, ProposalProvenance } from "../shared/types";

export function provenanceFixture(overrides: Partial<ProposalProvenance> = {}): ProposalProvenance {
  return {
    kind: "test_signals",
    label:
      "Test signals (not AI): deterministic-test / v1 encoder and scripted / scripted-test reasoner with 5 saved choices.",
    embeddingModel: "deterministic-test / v1",
    embeddingsGenuine: false,
    guidanceModel: "scripted / scripted-test",
    guidanceStatus: "completed",
    guidanceGenuine: false,
    comparisonsUsed: 5,
    preferenceMethod: "regularized_pairwise_logistic",
    excludedPhotoCount: 0,
    ...overrides,
  };
}

export function proposalFixture(overrides: Partial<Proposal> = {}): Proposal {
  const names = ["finish.jpg", "start.jpg", "podium.jpg", "crowd.jpg", "coach.jpg"];
  return {
    proposalId: "proposal-1",
    projectId: "project-1",
    version: 1,
    targetCount: 5,
    selectedCount: 5,
    isGenuineAi: false,
    provenance: provenanceFixture(),
    parameters: { weights: { prompt_relevance: 1, ai_guidance: 1, preference: 1 } },
    createdAt: "2026-11-04T12:00:00Z",
    recommendations: names.map((name, index) => ({
      photoId: `photo-${index}`,
      originalFilename: name,
      rank: index + 1,
      score: 2 - index * 0.25,
      contributions: { promptRelevance: 0.5, aiGuidance: 0.5, preference: 1 - index * 0.25 },
    })),
    ...overrides,
  };
}

export function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}
