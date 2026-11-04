# Issue 5 TDD Record — Pairwise Feedback

## Scope

A-05 adds a five-choice Alpha comparison workflow. It presents two distinct project photos,
persists the winner and loser, keeps both photos eligible, prevents repeated unordered pairs,
and stops at the configured comparison budget or when no unique pair remains.

The selector is intentionally described as a deterministic, exposure-balanced baseline. It is
not presented as adaptive preference learning; A-06 owns preference-score updates.

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
