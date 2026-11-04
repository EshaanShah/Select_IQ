# Issue 5 TDD Record — Pairwise Feedback

## Scope

A-05 adds a five-choice Alpha comparison workflow. It presents two distinct project photos,
persists the winner and loser, keeps both photos eligible, prevents repeated unordered pairs,
and stops at the configured comparison budget or when no unique pair remains.

The selector is intentionally described as a deterministic, exposure-balanced baseline. It is
not presented as adaptive preference learning; A-06 owns preference-score updates.

## AI responsibility boundary

A-05 does not call an LLM and should not be described as an AI model. Its responsibility is to
collect reliable, project-scoped human preference labels: the photographer preferred one presented
photo over another. Keeping this boundary narrow makes the interaction fast, deterministic, and
independently testable.

The stories divide AI responsibilities as follows:

- A-03 uses a real pretrained vision-language model to create compatible image/text embeddings.
- A-04 uses a genuine Groq-hosted generative model to interpret the creative brief into structured,
  auditable guidance.
- A-05 presents pairs and persists human winner/loser labels.
- A-06 performs lightweight preference learning from A-03 embeddings and A-05 labels. It may fit a
  regularized pairwise linear model or similarly simple ranker; it does not require an LLM call.

For A-06, a user choice can be represented by the embedding difference between the selected and
unselected photos. A learned weight vector then scores project photos using those visual features.
This is genuine machine learning because model parameters are updated from user examples and can
affect photos that were not directly compared. It should be described as a small project-specific
preference model, not as an LLM or sophisticated active learning system.

The eventual recommendation stage can combine distinct signals rather than asking one model to do
everything:

```text
A-04 brief guidance + A-06 learned preference signal + controlled ranking criteria
```

This boundary also means an A-05 reviewer does not need a Groq API key. A key is required only to
exercise the live A-04 generative-model path or the complete integrated demo. Secrets must remain in
local environment configuration and must never be committed.

## Red phase

The test specification was committed before production code:

- `4049a50` added selector, service, API, image-serving, and React comparison tests.
- `0aa4c0d` added persistence, budget, exhaustion, retry, and double-submit edge cases.
- `20f4a35` added the A-03 feature-preservation boundary and the A-05 migration-chain test.

The final red baseline contained 39 executable cases. Before implementation, the migration test
failed because revision `0005_pairwise_feedback` did not exist; backend suites failed collection
because the selector, service, and API dependency did not exist; and the frontend suite failed
because `ComparisonPage` did not exist.

The merged A-01 through A-04 baseline was verified separately before A-05 implementation:

- Backend: 98 passed, 2 permissioned-fixture skips, 2 external tests deselected.
- Frontend: 9 passed.

## Green implementation

- Added migration `0005_pairwise_feedback`, based on `0004_brief_interpretation`.
- Added project-scoped comparison persistence with unique sequence and normalized-pair constraints.
- Added deterministic pair selection that prioritizes photos with the fewest prior appearances.
- Added service validation for project membership, distinct IDs, valid winners, duplicates, and
  the comparison budget.
- Added FastAPI endpoints for the next pair, saved choices, and project-scoped JPEG content.
- Added a React comparison page with progress, completion, accessible errors, save locking, and
  retry-safe behavior.
- Added an explicit entry point from the completed-analysis workflow.
- Added final contract coverage for exact photo-ID/filename mapping and App-level navigation into
  the first comparison.

No committed A-05 tests were changed during the green phase.

## Verification

- Focused A-05 backend: 33 passed.
- Focused A-05 frontend: 6 passed.
- Backend regression excluding separately red A-06 files and external calls: 131 passed,
  2 permissioned-fixture skips, 2 external tests deselected.
- Full frontend: 16 passed.
- TypeScript and Vite production build: passed.
- Ruff, Python compilation, and whitespace validation: passed.

The repository also contains red A-06 tests for `PairwisePreferenceModel`, `PreferenceService`,
and its API dependency. Those are intentionally outside A-05 and were not modified.
