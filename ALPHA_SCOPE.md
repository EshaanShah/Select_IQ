# SelectIQ — Authoritative Alpha Scope

**Deadline:** November 5, 2026  
**Objective:** Deliver a narrow, locally runnable, genuinely AI-driven photo-culling vertical slice with test-first evidence and honest photographer validation.

This document controls Alpha implementation decisions. The larger 300-photo research MVP described elsewhere is Beta/later scope.

## Alpha commitment

| Dimension | Alpha | Beta / later |
|---|---|---|
| Gallery | 10–30 JPEGs; test at 30 | Approximately 300 and throughput benchmarking |
| Demo gallery | 15–20 consented photographs | Large participant galleries |
| Target | User-selected; demo target 5 | Approximately 80 of 300 |
| Comparisons | 5–10 saved choices; demo 5 | 20–40 adaptive comparisons |
| AI | Real pretrained image/text embeddings plus a genuine structured generative-model call that affects an auditable decision | Calibrated preference learning and deeper multimodal reasoning |
| Proposal | Deterministic top-K using prompt and choice signals | Collection-level optimization and advanced redundancy control |
| Review | Grid, removal without replacement, CSV filenames | Advanced uncertainty queue and explanations |
| Runtime | Local Apple Silicon Mac, local project storage, no authentication | Hardened deployment if warranted |
| Validation | Permissioned gallery and honest target-photographer feedback | Larger controlled research study |

## Canonical demo

1. Load 15–20 permissioned JPEGs.
2. Enter a creative brief and choose a target of 5.
3. Run real image/text inference and one genuine structured generative-model step.
4. Complete 5 saved A/B choices and show that prompt/choices affect ranking.
5. Generate 5 distinct recommendations.
6. Remove one recommendation, leaving 4.
7. Export a CSV containing those 4 exact filenames.

## Architecture constraint

Use the simplest genuinely testable local architecture: React/Vite, FastAPI, local project directories, and SQLite or an equivalently simple transactional local metadata store. Do not add Docker, PostgreSQL, Redis, S3, cloud deployment, or a large agent framework for Alpha.

## Scope-cut rule

Cut sophisticated similarity grouping, advanced uncertainty, extensive explanations, and polish before cutting genuine AI integration, preference-sensitive ranking, the complete demo flow, tests, or real validation.

See [SelectIQ_User_Stories.md](SelectIQ_User_Stories.md) for the authoritative Alpha issue map. The PRD and TDD describe the broader product direction; any 300-input, 80-output, or 20–40-comparison language there is Beta/later unless explicitly labeled otherwise.
