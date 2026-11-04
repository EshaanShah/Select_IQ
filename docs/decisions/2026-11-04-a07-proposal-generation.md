# 2026-11-04 — A-07 proposal generation

**Status:** Accepted for Alpha. Built on the merged A-02, A-03, A-04, A-05, and A-06 work.

## Context

A-07 must return exactly K distinct, valid photos, deterministically, using the prompt, genuine AI guidance, and saved choices. A losing photo must stay eligible. The Alpha scope asks for a deterministic top-K, not collection-level optimization, and it forbids presenting test or fallback output as AI.

## Decision

1. **Signals.** `application/proposal_signals.ProjectSignalProvider` builds one `PhotoSignals` per eligible photo:
   - `prompt_relevance`: A-03 CLIP image–brief similarity (`PhotoFeature.brief_relevance`).
   - `ai_guidance`: the A-04 guided score from `BriefInterpreter.ranking()`. It's used only when the latest interpretation **completed for the current brief**. Otherwise the signal is absent; nothing is substituted for it.
   - `preference`: the A-06 `PreferenceService.scores()` from the saved A/B choices (A-05).
2. **Eligibility.** A photo is eligible only if CLIP analysis completed for the current brief. Photos whose analysis failed are excluded and counted (`excludedPhotoCount`). If the target is larger than the eligible count, the error says how many photos finished analysis and how many failed.
3. **Scoring** (`intelligence/curator.py`).
   - Each signal is min-max normalized across the eligible photos. Missing or constant signals contribute 0.
   - The score is the weighted sum of the normalized signals.
   - The proposal is the top K by score, with exact ties broken by photo ID.
4. **Weights.** Prompt relevance and AI guidance are each 1.0. Preference is \(2n/(n+5)\) for \(n\) saved choices. That's 0 with no choices, 1.0 at the 5-choice Alpha budget, and it approaches 2.0. This follows TDD §12.3: the photographer's demonstrated preferences should carry substantial weight, but reliance grows as evidence accumulates. Every proposal stores its weights in `parameters.weights`.
5. **Loser eligibility.** Preference is one weighted term. A photo that lost every comparison is still ranked, and it's selected if its other signals are strong enough (regression-tested).
6. **Provenance.** Every proposal stores a `SignalProvenance`: the embedding model, the guidance model, the guidance status, the number of choices used, the preference method, and the excluded-photo count. Whether the adapters are genuine comes from the wiring in `api/dependencies.py` (`SELECTIQ_MODEL_ADAPTER=openclip`, `SELECTIQ_REASONER=groq`). It is not inferred from model names. The provenance has one of three kinds:
   - `ai_informed`: real OpenCLIP and a completed Groq interpretation (`isGenuineAi: true`).
   - `partial_ai`: real OpenCLIP, but Groq guidance failed, hasn't run, or came from the offline stand-in. The label says "AI interpretation unavailable — using basic relevance".
   - `test_signals`: the deterministic test encoder. The label says "Test signals (not AI)".
7. **Target and API.**
   - `POST /projects/{id}/recommendations` uses the A-02 saved target. An optional strict-integer `targetCount` overrides it.
   - It returns 422 when there's no brief or target, when analysis hasn't run, or when the target is invalid, and 404 for an unknown project.
   - `GET` returns the latest version.
8. **Persistence.** Proposals are versioned in `proposals` and `proposal_items` (migration `0006_recommendation_proposals`). Regenerating creates a new version, so proposals made before and after A/B choices stay auditable.

## Consequences

- Fixed inputs reproduce the same proposal. The encoder, the cached embeddings, the interpretation, and `PairwisePreferenceModel(seed=0)` are all deterministic for the same files, brief, and choices.
- Redundancy control and uncertainty grouping remain Beta scope, as the Alpha scope-cut rule specifies.
- A live check with OpenCLIP and Groq needs `GROQ_API_KEY` in `.env` and a one-time download of the CLIP weights.
