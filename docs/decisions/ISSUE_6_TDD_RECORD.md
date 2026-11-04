# Issue 6 TDD Record — Preference Update

## Scope

A-06 turns A-05 winner/loser choices into project-specific preference scores over the A-03 image
embeddings. The Alpha implementation is a regularized pairwise linear ranker. It is lightweight
machine learning, not an LLM call, neural-network fine-tuning, or sophisticated active learning.

## Model

For a saved choice where photo A wins over photo B, the training feature is the signed embedding
difference:

```text
d = embedding(A) - embedding(B)
P(A preferred over B) = sigmoid(w · d)
score(photo) = w · embedding(photo)
```

Each winner-minus-loser observation is paired with its negation and the opposite class label. This
gives logistic regression both classes and prevents pair-order bias. L2 regularization shrinks the
project-specific weight vector toward neutral because the Alpha has only five comparison choices.
Scores are mean-centered so they are explicitly relative within the current project.

The model is retrained from the small persisted comparison history whenever scores are requested.
That keeps the implementation deterministic and avoids adding model-state persistence. It can score
analyzed photographs that were not directly compared because all photos share the A-03 embedding
space.

## Red phase

- `032b034` added the initial synthetic model, service, and API tests.
- `4f18b4a` injected the A-03 embedding cache and added deterministic ties, missing-cache-file
  handling, and unusable-comparison handling.

The final red baseline contained 30 cases:

- 17 preference-model unit tests.
- 9 project-service integration tests.
- 4 API contract tests.

Before implementation, collection failed because `PairwisePreferenceModel`, `PreferenceService`,
and the preference API dependency did not exist. The synchronized A-01 through A-05 baseline stayed
green with 131 backend tests and 16 frontend tests.

## Green implementation

- Added `PairwisePreferenceModel` using regularized scikit-learn logistic regression.
- Added validation for unknown photos, self-comparisons, incompatible dimensions, non-finite
  features, and invalid regularization.
- Added neutral zero-choice scores, fixed-seed reproducibility, mean-centered project-relative
  scores, model versioning, and the honest method label `regularized_pairwise_logistic`.
- Added `PreferenceService` to load validated A-03 vectors, exclude missing or unanalyzed photos,
  exclude failed photos even when stale feature records remain, read only the current project's
  A-05 choices, and count only usable comparisons.
- Added `GET /projects/{project_id}/preferences` with deterministic score ordering, `404` for an
  unknown project, and `409` when no usable analysis exists.

No A-06 test was changed or weakened during the green phase.

## Verification

- Focused A-06: 31 passed.
- Backend non-external suite: 162 passed, 2 permissioned-fixture skips, 2 external tests deselected.
- Frontend: 16 passed.
- TypeScript/Vite production build: passed.
- Ruff, Python compilation, and whitespace validation: passed.

## Honest claims

This implementation may be described as a project-specific regularized pairwise preference model
trained from human comparisons over pretrained visual embeddings. It must not be described as an
LLM, encoder fine-tuning, calibrated preference probability, or adaptive comparison selection.
