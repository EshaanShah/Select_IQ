# SelectIQ Alpha Repository Structure

**Status:** Approved Alpha structure proposal<br>
**Scope:** The ten finalized Alpha user stories in `SelectIQ_User_Stories.md`<br>
**Goal:** Keep the three-day Alpha implementation small, testable, local-first, and easy to explain during the engineering-methodology presentation.

> [ALPHA_SCOPE.md](ALPHA_SCOPE.md) and [SelectIQ_User_Stories.md](SelectIQ_User_Stories.md) are authoritative. Advanced uncertainty, 300-photo scale, and research-grade curation remain Beta/later scope.

---

# 1. Structure

```text
Select_IQ/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx
│   │   │   └── routes.tsx
│   │   ├── features/
│   │   │   ├── gallery-upload/
│   │   │   ├── creative-brief/
│   │   │   ├── comparisons/
│   │   │   ├── gallery-review/
│   │   │   └── evaluation/
│   │   ├── shared/
│   │   │   ├── components/
│   │   │   ├── api/
│   │   │   └── types/
│   │   ├── test/
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/
│   ├── src/
│   │   └── selectiq/
│   │       ├── api/
│   │       │   ├── main.py
│   │       │   ├── dependencies.py
│   │       │   └── routes/
│   │       │       ├── projects.py
│   │       │       ├── comparisons.py
│   │       │       ├── recommendations.py
│   │       │       └── feedback.py
│   │       ├── domain/
│   │       │   ├── models.py
│   │       │   ├── enums.py
│   │       │   └── errors.py
│   │       ├── application/
│   │       │   ├── project_service.py
│   │       │   ├── comparison_service.py
│   │       │   ├── recommendation_service.py
│   │       │   └── feedback_service.py
│   │       ├── intelligence/
│   │       │   ├── brief_interpreter.py
│   │       │   ├── feature_extractor.py
│   │       │   ├── similarity.py
│   │       │   ├── preference_model.py
│   │       │   ├── pair_selector.py
│   │       │   ├── curator.py
│   │       │   └── uncertainty.py
│   │       ├── infrastructure/
│   │       │   ├── image_store.py
│   │       │   ├── project_repository.py
│   │       │   ├── model_adapters.py
│   │       │   └── settings.py
│   │       └── jobs/
│   │           └── analyze_gallery.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── contract/
│   │   └── conftest.py
│   └── pyproject.toml
│
├── tests/
│   ├── e2e/
│   │   └── alpha_workflow.spec.ts
│   └── fixtures/
│       ├── common/
│       ├── sports/
│       │   ├── manifest.json
│       │   ├── expected_behaviors.json
│       │   └── README.md
│       └── retirement/
│           ├── manifest.json
│           ├── expected_behaviors.json
│           └── README.md
│
├── scripts/
│   ├── dev.sh
│   ├── test.sh
│   ├── benchmark_gallery.py
│   └── simulate_comparisons.py
│
├── var/
│   ├── projects/
│   ├── cache/
│   ├── exports/
│   └── selectiq.sqlite3
│
├── docs/
│   ├── evaluation/
│   └── decisions/
│
├── .env.example
├── .gitignore
├── README.md
├── ALPHA_REPO_STRUCTURE.md
├── SelectIQ_PRD.md
├── SelectIQ_TDD.md
└── SelectIQ_User_Stories.md
```

Only directories needed by the Alpha stories should be created. Do not add empty Beta-oriented packages in anticipation of future features.

---

# 2. Responsibility Boundaries

## Frontend

The frontend renders the photographer workflow and calls the API. It must not contain image-scoring, preference-learning, curation, or uncertainty algorithms.

- `gallery-upload/`: file selection and accepted/rejected counts. Covers A-01.
- `creative-brief/`: prompt, target, and auditable AI interpretation. Covers A-02 and A-04.
- `comparisons/`: A/B display and saved feedback. Covers A-05 and A-06.
- `gallery-review/`: deterministic top-K proposal, removal, and CSV export. Covers A-07 and A-08.
- `evaluation/`: end-to-end flow and satisfaction feedback. Covers A-09 and A-10.
- `shared/api/`: the only frontend layer that makes HTTP calls.
- `shared/types/`: API-facing TypeScript contracts; no business logic.

## API

The API validates requests, invokes application services, and returns typed responses. Routes must remain thin and must not implement ranking logic.

- `projects.py`: create project, upload gallery, submit brief, set target, and read processing state.
- `comparisons.py`: request the next pair and submit a preference.
- `recommendations.py`: generate/read proposal, remove a selection, and export filenames.
- `feedback.py`: submit the 1–5 satisfaction rating and optional comments.

## Domain

`domain/` contains the stable language of the product: project, photograph, creative brief, comparison, recommendation, uncertainty reason, selection state, and feedback. Domain objects must not import FastAPI, React, SQLite, OpenCV, or a specific AI provider.

## Application services

Application services coordinate complete use cases. They depend on domain types and explicit infrastructure interfaces.

- `project_service.py`: A-01 and A-02 orchestration.
- `comparison_service.py`: A-05 and A-06 workflow.
- `recommendation_service.py`: A-07 and A-08 workflow.
- `feedback_service.py`: A-10 workflow and evaluation metrics.

## Intelligence

`intelligence/` contains the custom selection behavior that differentiates SelectIQ.

- `brief_interpreter.py`: turns free text into validated positive, negative, neutral, and contextual evidence.
- `feature_extractor.py`: generates technical signals and visual representations without making final aesthetic judgments.
- `similarity.py`: exact duplicate, near-duplicate, burst, and related-moment evidence.
- `preference_model.py`: learns project-specific ranking behavior from A/B choices.
- `pair_selector.py`: chooses informative comparisons within the interaction budget.
- `curator.py`: creates the target-sized, redundancy-aware proposal.
- `uncertainty.py`: reserved for Beta/later; it is not an Alpha completion dependency.

## Infrastructure

Infrastructure isolates replaceable technical details.

- `image_store.py`: local project folders, thumbnails, and source-file safety.
- `project_repository.py`: SQLite persistence for project state, comparisons, proposals, removals, exports, and feedback.
- `model_adapters.py`: pretrained encoder and optional multimodal provider interfaces.
- `settings.py`: environment-driven paths, limits, model choices, and feature flags.

## Jobs

The Alpha uses one local analysis job runner. Do not add Redis, Celery, a distributed queue, or cloud-worker infrastructure.

---

# 3. Test Structure

## Backend unit tests

Mirror the production module being tested:

```text
backend/tests/unit/
├── test_brief_interpreter.py
├── test_feature_extractor.py
├── test_similarity.py
├── test_preference_model.py
├── test_pair_selector.py
├── test_curator.py
└── test_uncertainty.py
```

These tests use small deterministic inputs and synthetic feature records. They must run without loading a full gallery or calling an external model.

## Backend integration tests

```text
backend/tests/integration/
├── test_project_ingestion.py
├── test_comparison_flow.py
├── test_recommendation_flow.py
├── test_review_and_export.py
└── test_feedback_flow.py
```

These tests exercise isolated SQLite storage, the local image store, application services, and controlled fake model adapters together.

## API contract tests

Contract tests verify request validation, response schemas, IDs, counts, error behavior, and project isolation. They should not duplicate ranking-algorithm tests.

## Frontend tests

Component tests stay beside their feature when practical, for example:

```text
frontend/src/features/comparisons/ComparisonPage.test.tsx
frontend/src/features/gallery-review/GalleryReviewPage.test.tsx
```

Use mocked API responses to test visible states and interactions.

## End-to-end test

Maintain one primary Playwright scenario in `tests/e2e/alpha_workflow.spec.ts`:

1. Import a fixture gallery.
2. Submit a creative brief and target count.
3. Wait for deterministic fake analysis.
4. Complete controlled A/B comparisons.
5. Generate the proposal.
6. Remove a recommendation.
7. Export filenames.
8. Submit satisfaction feedback.

Run the same workflow against both the sports and retirement fixture manifests when time permits. The fast required CI path may use synthetic records, while local evaluation uses permissioned images.

---

# 4. Fixture Organization

`tests/fixtures/sports/manifest.json` and `tests/fixtures/retirement/manifest.json` describe test inputs without requiring private photographs in Git.

Each manifest record should include:

- Stable fixture ID.
- Scenario and moment category.
- Relative or private-local image reference.
- Expected contextual signals.
- Duplicate or burst group, when applicable.
- Intentional versus accidental technical characteristic annotations.
- Permission/provenance status.

`expected_behaviors.json` describes assertions such as:

- A peak-action sports frame may outrank a sharp empty-action frame.
- Requested panning blur applies to relevant sports action, not every photograph.
- A low-light retirement embrace may outrank a technically cleaner detail photograph.
- A sharp retirement group portrait is not penalized or boosted by an unrelated sports preference.
- Burst and ceremony sequences reduce repetition without enforcing one image per group.

Real galleries belong outside the tracked repository. Tests locate them through an environment setting documented in `.env.example`, such as `SELECTIQ_FIXTURE_ROOT`, or use small publishable derived fixtures with explicit permission.

---

# 5. Local Runtime Data

The entire `var/` directory is ignored by Git.

- `var/projects/`: uploaded project copies and thumbnails.
- `var/cache/`: embeddings, metrics, and similarity artifacts.
- `var/exports/`: generated filename lists.
- `var/selectiq.sqlite3`: local Alpha structured state.

The application must never modify the photographer's source files. Uploaded working copies, generated thumbnails, embeddings, exports, and the SQLite database are disposable local artifacts.

---

# 6. Dependency Direction

```text
React features
    ↓
typed API client
    ↓
FastAPI routes
    ↓
application services
    ↓
domain + intelligence
    ↓
infrastructure adapters
```

Rules:

1. React never imports Python or implements selection algorithms.
2. FastAPI routes never contain preference or curation math.
3. Intelligence modules never depend on HTTP or UI types.
4. Domain types never depend on libraries or providers.
5. External models are accessed only through adapters.
6. Tests replace adapters with deterministic fakes.
7. One project’s brief and learned preferences never affect another project.

---

# 7. Story-to-Code Map

| Story | Primary backend modules | Primary frontend feature | Primary tests |
|---|---|---|---|
| A-01 | `project_service`, `image_store`, `projects` route | `gallery-upload` | ingestion integration and API contract |
| A-02 | project validation and repository | `creative-brief` | prompt/target contract tests |
| A-03 | `feature_extractor`, model adapters, cache | processing state | feature and cache tests |
| A-04 | generative-model adapter, schema validation | `creative-brief` | real smoke test plus failure contracts |
| A-05 | `comparison_service` | `comparisons` | comparison-flow tests |
| A-06 | `preference_model` | `comparisons` | controlled before/after ranking tests |
| A-07 | `curator`, `recommendation_service` | `gallery-review` | exact-K and sensitivity tests |
| A-08 | recommendation state and export | `gallery-review` | removal/export integration tests |
| A-09 | all Alpha services | complete workflow | Playwright happy path and failure smoke test |
| A-10 | `feedback_service`, repository | `evaluation` | feedback linkage tests |

---

# 8. Explicitly Outside the Alpha Structure

Do not add these unless the Alpha scope changes:

- Authentication or user-account packages.
- Cloud object storage.
- PostgreSQL, Redis, Celery, or Kubernetes.
- Payment, subscription, or analytics SDKs.
- RAW, video, Lightroom, or Capture One integrations.
- Cross-project preference profiles.
- Multi-user collaboration.
- Native mobile applications.
- A general plugin system.
- Microservices or separate deployed workers.

This structure is intentionally a modular monolith. It creates clean boundaries for testing without adding deployment complexity the Alpha does not need.

