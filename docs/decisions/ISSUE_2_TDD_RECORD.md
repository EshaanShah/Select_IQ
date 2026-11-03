# Issue 2 Engineering Record — Prompt and Target

**Branch:** `issue-2-prompt-target`

**Red-test commit:** `753b129`

**Story:** A-02 — Prompt and target

**Status:** Green; A-02 implementation complete

## Why this record exists

This document records what was done, why it was done, and how to explain the engineering choices in a code review, presentation, or technical interview. It should be updated when the implementation turns the tests green.

## Scope discovery

The repository originally described a larger US-02 story in which AI interpreted contextual creative preferences. After synchronizing with `main`, the authoritative Alpha scope had changed:

- `ALPHA_SCOPE.md` and `SelectIQ_User_Stories.md` now control implementation decisions.
- Current Issue 2 is A-02, which only stores and restores a nonempty prompt and a valid target.
- Real image/text embeddings belong to A-03.
- Genuine generative-model interpretation belongs to A-04.
- The Alpha gallery is 10–30 photographs, with a typical target of 5, rather than the earlier 300-photo research scope.

This prevented scope creep. No LLM adapter, prompt interpretation schema, ranking behavior, or contextual blur logic was added to Issue 2.

## A-02 acceptance criteria

The tests define these behaviors:

1. Store a nonempty free-text creative brief.
2. Store an integer target from 1 through the accepted-photo count, inclusive.
3. Reject blank prompts and invalid targets with clear errors.
4. Restore the prompt and target from the local project session.
5. Accept the canonical target of 5 for a 15–20-photo demo gallery.

## TDD process used

### 1. Inspect before changing

The existing domain, application service, repository, API, frontend, migrations, and tests were inspected first. The implementation currently has:

- A `CreativeBrief` domain type and `Project.target_count` field.
- SQLite-backed project and photograph persistence.
- Project creation, JPEG ingestion, accepted counts, and session restoration.
- No prompt/target repository fields, service methods, endpoint, API client, or form.

### 2. Write tests before production code

Tests were added at four boundaries:

| Layer | Purpose |
|---|---|
| Service/unit | Define validation rules and atomic update behavior. |
| SQLite integration | Prove values survive a fresh service instance and remain project-isolated. |
| FastAPI contract | Define request/response shapes, status codes, and strict JSON types. |
| React component | Define the photographer-facing save, restore, and validation workflow. |

### 3. Confirm the frontend red phase

After installing the locked frontend dependencies, the test run reported:

```text
Test Files  1 failed (1)
Tests       4 failed | 2 passed (6)
```

The two pre-existing gallery-import tests passed. All four new A-02 frontend tests failed because the `Creative brief` control does not exist yet. This is the intended first failure and shows that the new tests detect missing A-02 behavior without regressing A-01.

The frontend TypeScript build also passed, confirming that the test file itself was type-correct. Backend tests were syntax-checked during the red phase; their dependencies were installed into an isolated temporary environment for the green phase.

## Tests added

### Service validation

- Valid prompt and target are returned on the project.
- Target 5 is accepted for both 15- and 20-photo galleries.
- Empty, ASCII-whitespace, newline, and Unicode-whitespace prompts are rejected.
- Zero and negative targets are rejected.
- Floats, numeric strings, booleans, and null are rejected rather than coerced.
- A target greater than the accepted count is rejected.
- A target equal to the accepted count is accepted.
- A positive target is rejected when the project has no accepted photos.
- Unicode, punctuation, emoji, and surrounding whitespace are preserved exactly in nonblank input.
- A valid replacement updates both prompt and target.
- An invalid replacement changes neither saved value.

The boolean case is deliberate: in Python, `bool` subclasses `int`, so a naïve `isinstance(target, int)` check would incorrectly accept `True` as target 1.

### SQLite integration

- Prompt and target survive creation of a fresh repository/service instance.
- Two projects in the same database retain independent prompt/target values.

These tests prevent an implementation that only mutates an in-memory `Project` object or forgets to constrain an update by project ID.

### API contract

- `POST /projects/{project_id}/brief` saves prompt and target.
- `GET /projects/{project_id}/status` restores them.
- Unset prompt and target are represented explicitly as `null`.
- Blank prompts return a clear 422 response.
- Targets below 1 or above the accepted count return 422.
- Float, string, boolean, and null targets return 422 without coercion.
- A syntactically valid but unknown project ID returns 404.

### React workflow

- A photographer can upload a demo-sized gallery, enter a brief and target, and save them.
- The JSON request contains a numeric target rather than the input element's string value.
- A restored project repopulates both controls.
- Blank prompts are blocked with an accessible error.
- Targets above the accepted count are blocked with an accessible error.

## Test data strategy

These tests do not need a real participant gallery.

- Backend fixtures generate tiny, valid 16-by-12 JPEGs with Pillow. They exercise real JPEG decoding and storage without private data.
- Frontend tests use browser `File` objects and mocked HTTP responses because they test UI state and request construction, not image decoding.
- Temporary SQLite databases and temporary project directories isolate every test run.

Real permissioned photographs become necessary for A-03 model smoke tests, A-04 genuine AI behavior, ranking evaluation, the end-to-end demo, and participant validation. Using a real gallery for A-02 would make the suite slower and less deterministic without improving coverage of prompt/target rules.

## Implemented solution

The tests drove this implementation:

1. Add nullable prompt and target fields to the project persistence model through a new Alembic migration.
2. Reconstruct `CreativeBrief` and `target_count` when loading a project.
3. Add an atomic repository operation that saves both values together.
4. Add `ProjectService.set_prompt_and_target()` and `get_project()` with domain validation.
5. Add a strict FastAPI request model and `POST /projects/{id}/brief`.
6. Include prompt and target in project status.
7. Add shared TypeScript contracts and an API-client function.
8. Add accessible prompt/target controls, restoration, validation, and save feedback.
9. Run the focused tests until green, then run the complete regression suite.

The service uses a trimmed copy only to determine whether the prompt is blank. It stores the original nonblank text so Unicode and user formatting are not silently changed. The API uses a strict integer contract, and the repository writes prompt and target in one transaction.

## Green-phase evidence

The complete backend suite passed:

```text
50 passed, 2 skipped in 2.80s
```

The two skips are the permissioned sports and retirement gallery tests; those private fixtures were not present. No A-02 test was skipped.

The complete frontend component suite passed:

```text
Test Files  1 passed (1)
Tests       6 passed (6)
```

The TypeScript/Vite production build completed successfully. The Alembic migration was also exercised in both directions against a temporary SQLite database: upgrade added `brief_text` and `target_count`, and downgrade removed both columns.

Focused backend line coverage for the three modules changed by A-02 was 97% overall:

| Module | Line coverage |
|---|---:|
| `api/routes/projects.py` | 96% |
| `application/project_service.py` | 99% |
| `infrastructure/project_repository.py` | 97% |

## Likely mutation tests

Once the implementation is green, mutation testing should target the highest-value rules:

- Change `target > accepted_count` to `target >= accepted_count`.
- Remove the target-lower-bound check.
- Allow `bool` through the integer check.
- Remove whitespace normalization from blank detection.
- Update prompt before target validation, creating a partial write.
- Remove the project-ID filter from persistence.

The current tests should kill each of these mutations. A surviving mutation would identify a missing or weak assertion.

## Interview and presentation talking points

### Why test at multiple layers?

Each layer protects a different contract. Service tests specify business rules, integration tests prove durable and isolated persistence, API tests prevent coercion and schema regressions, and React tests protect the user workflow. This is not duplicate testing because the failure boundaries differ.

### Why reject numeric strings instead of converting them?

Strict contracts prevent ambiguous behavior across clients. The browser converts its number input before sending JSON; the backend independently rejects malformed or nonconforming clients.

### Why preserve surrounding whitespace if blank whitespace is invalid?

Validation and storage serve different purposes. Trimming is appropriate for detecting an empty semantic value, while the original accepted creative brief remains authoritative user input.

### Why save prompt and target atomically?

They form one workflow decision. A partial write could associate a revised prompt with an old target after a failed update, making the restored session inconsistent.

### Why not test with real photos?

Image content is irrelevant to A-02; only accepted count matters. Synthetic valid JPEGs provide deterministic, private, fast tests. Real photos are reserved for stories where their visual content affects inference or ranking.

### What demonstrates true TDD here?

The tests and contracts were committed before production behavior. The red frontend run was captured, existing A-01 tests stayed green, and the future implementation plan follows the failing boundaries rather than retrofitting tests afterward.

## Git history and isolation

- The test work was first committed as `753b129 Add red tests for A-02 prompt and target`.
- The feature branch was renamed to `issue-2-prompt-target`, matching the Issue 1 naming style.
- `main` was checked directly and remained clean and aligned with `origin/main` before continuing feature work.
- Generated `frontend/node_modules` and `frontend/dist` content is ignored and was not committed.

## Green-phase checklist

- [x] Preserve the committed frontend red-test evidence.
- [x] Add migration and persistence behavior.
- [x] Implement service validation and atomic update.
- [x] Implement API contract.
- [x] Implement frontend workflow.
- [x] Run focused backend and frontend tests.
- [x] Run the complete regression suite.
- [x] Add focused backend coverage numbers (97%).
- [ ] Run targeted mutation testing.
- [x] Record green-phase test evidence in this document.
