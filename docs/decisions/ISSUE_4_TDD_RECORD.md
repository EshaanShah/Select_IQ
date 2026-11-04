# Issue 4 Engineering Record — LLM-Guided Brief Interpretation

**Branch:** `issue-4-brief-interpretation`

**Red-test commit:** `5971966` (backend); the frontend tests were added red in the same session before `InterpretationPanel` existed

**Story:** A-04 — LLM-guided brief interpretation

**Status:** Green on deterministic tests; real Groq smoke test pending a `GROQ_API_KEY`

## Acceptance criteria and where they are proven

| Criterion | Implementation | Tests |
|---|---|---|
| Invoke a genuine generative text or multimodal model | `GroqBriefReasoner` calls Groq's OpenAI-compatible chat API with a vision model and a strict JSON schema | `test_groq_reasoner.py` (request shape, images, schema); `test_groq_smoke.py` (`real_llm`, live call) |
| Ground the request in the brief and image-derived evidence | The request carries the brief, target, each photo's CLIP brief similarity, and labeled contact sheets of the actual photographs | `test_completed_interpretation_is_grounded_persisted_and_changes_ranking`; `test_sends_brief_evidence_images_and_strict_schema` |
| Validate structured output and allowed photo IDs | `parse_interpretation` rejects non-JSON, missing/mistyped fields, oversize descriptors, duplicate notes, and any label not in the gallery; labels map back to real photo IDs server-side | `test_brief_interpretation_parsing.py`; `test_failures_are_recorded_and_ranking_falls_back[unknown_photo_id]` |
| A failed call cannot masquerade as success | Every failure path persists a `failed` interpretation with an error code and no guided scores; ranking reports `basis = brief_relevance`; the UI shows "AI interpretation unavailable — using basic relevance" | timeout / malformed / invented-ID / rate-limit / request-limit tests; `labels the degraded fallback and retries the model call` |
| Valid guidance affects selection or an auditable downstream criterion | Descriptors are embedded with CLIP; each photo gets a stored `guided_score` with its components and a text explanation; `BriefInterpreter.ranking()` is the input A-07 will consume | `test_model_guidance_changes_ranking_relative_to_brief_relevance`; `test_photo_notes_use_real_ids_and_adjust_scores` |

## Key design decisions

### The model guides; it does not rank

The model returns short visual descriptors and optional notes, not a ranking. That keeps the
decision auditable: every guided score is
`mean(sim to favor) − mean(sim to avoid) ± 0.05 note`, and the stored explanation names the
closest descriptor and any note. It also keeps scores comparable across runs and providers.

### Contact sheets instead of one image per photo

Groq's free vision model accepts three images per request. Photos are tiled 12 per sheet with
a `P01`-style caption, so a 30-photo Alpha gallery fits in one request. Short labels are also
easier for the model to copy exactly, and the server-side label → photo ID map makes invented
IDs detectable instead of silently wrong.

### Descriptors are length-checked for CLIP

CLIP's text encoder truncates at 77 tokens. Descriptors are limited to 12 words / 100
characters, and over-long descriptors reject the whole response rather than being truncated.

### Strict failure semantics

An invented photo ID rejects the entire response, not just that note: an output that
hallucinates one reference is not trusted for the rest. Raw completions are stored even for
failed attempts so a reviewer can see exactly what the model said.

### Cost control

Every interpretation records duration and token usage. Projects are capped at
`SELECTIQ_REASONER_MAX_REQUESTS_PER_PROJECT` provider calls (default 20); attempts that never
reached the provider (missing key, limit reached) do not count. Busy (429/5xx) and timeout
responses are retried twice with backoff before failing.

### Runner integration

Interpretation runs on the same single analysis worker after CLIP scoring succeeds, so the
CLIP model is never used concurrently. Interpretation failures never mark photographs as
failed; analysis results remain valid. Re-analyzing an unchanged gallery does not call the
model again; galleries analyzed before A-04 are interpreted on the next analyze request.

## Data model

- `brief_interpretations`: one row per attempt (status, provider, model, prompt hash, parsed
  output, raw response, error code/message, duration, tokens, sequence).
- `guided_scores`: one row per photograph per completed interpretation (guided score,
  descriptor score, note adjustment, brief relevance, explanation).

Migration: `0004_brief_interpretation`.

## API

- `GET /projects/{id}/interpretation` → status (`not_started`, `running`, `completed`,
  `failed`), interpretation fields, `rankingBasis`, and ranked photographs.
- `POST /projects/{id}/interpretation` → 202; 409 until analysis is complete for the current
  brief.

## Known limitations

- Free-tier Groq models and limits change; the model ID is configurable via
  `SELECTIQ_GROQ_MODEL`.
- Contact-sheet tiles are 320 px, which is enough for smiles, lighting, and action at Alpha
  scale but loses fine detail.
- Guided scores are not yet used to pick the final gallery; A-07 consumes `ranking()`.
