# SelectIQ — Alpha User Stories

**Status:** Authoritative three-day Alpha scope<br>
**Alpha gallery:** 10–30 valid JPEGs; demo with 15–20<br>
**Alpha target:** User-selected, typically 5<br>
**Alpha feedback:** 5–10 saved A/B choices; demo with 5

The Alpha is a narrow, locally runnable, genuinely AI-driven vertical slice. The 300-photo, 80-selection, 20–40-comparison research MVP is Beta/later scope.

Every issue is complete only when its acceptance criteria are met, tests were observed failing before implementation, relevant tests pass afterward, and evidence is linked from GitHub.

## Delivery dependency map

Dependencies are implementation prerequisites, not merely the order in which the demo is shown.

```text
A-01 Gallery upload
├── A-02 Prompt and target
└── A-03 AI feature extraction
    ├── A-04 LLM-guided brief interpretation
    └── A-05 Pairwise feedback
        └── A-06 Preference update

A-02 + A-03 + A-04 + A-06
└── A-07 Proposal generation
    └── A-08 Review and export
        └── A-09 End-to-end demo
            └── A-10 Satisfaction collection
```

| Issue | Depends on | Unlocks |
|---|---|---|
| A-01 | None | A-02, A-03 |
| A-02 | A-01 | A-04, A-07 |
| A-03 | A-01 | A-04, A-05, A-06, A-07 |
| A-04 | A-02, A-03 | A-07 |
| A-05 | A-01, A-03 | A-06 |
| A-06 | A-03, A-05 | A-07 |
| A-07 | A-02, A-03, A-04, A-06 | A-08 |
| A-08 | A-07 | A-09 |
| A-09 | A-01 through A-08 | A-10 |
| A-10 | A-09 | None |

---

# A-01 — Gallery upload

**Depends on:** None<br>
**Unlocks:** A-02 (#2), A-03 (#3)

## User story

As a photographer, I want to upload JPEGs so that SelectIQ can analyze my gallery.

## Acceptance criteria

- Accept 10–30 JPG/JPEG files for the Alpha workflow.
- Reject invalid formats and corrupt files with clear errors.
- Assign unique internal IDs while preserving original filenames.
- Duplicate filenames do not overwrite one another.
- Display the accepted count and never modify source files.

## Tests written first

- Valid upload; bad extension/content; corrupt JPEG; duplicate names; empty upload.
- Thirty valid JPEGs are all accounted for.
- Source hashes remain unchanged.

---

# A-02 — Prompt and target

**Depends on:** A-01 (#1)<br>
**Unlocks:** A-04 (#4), A-07 (#7)

## User story

As a photographer, I want to describe my story and set a target so that recommendations reflect my intent.

## Acceptance criteria

- Store a nonempty free-text creative brief.
- Store an integer target from 1 through the accepted-photo count.
- Reject blank prompts and invalid targets with clear errors.
- Reload prompt and target from the local project session.

## Tests written first

- Valid prompt/target; blank prompt; zero, negative, fractional, and too-large targets.
- A target of 5 is accepted for a 15–20-photo demo gallery.

---

# A-03 — AI feature extraction

**Depends on:** A-01 (#1)<br>
**Unlocks:** A-04 (#4), A-05 (#5), A-06 (#6), A-07 (#7)

## User story

As a photographer, I want images analyzed so that the product can compare visual content.

## Acceptance criteria

- Every accepted photo receives a cached embedding from a real pretrained vision-language model.
- The prompt receives a compatible representation used for prompt-image relevance.
- Reanalysis reuses cached embeddings.
- Analysis failures are surfaced and never presented as successful inference.

## Tests written first

- Embedding shape and finite values; photo-ID alignment; cache reuse; injected inference failure.
- Small real-model smoke test with representative permitted input.

---

# A-04 — LLM-guided brief interpretation

**Depends on:** A-02 (#2), A-03 (#3)<br>
**Unlocks:** A-07 (#7)

## User story

As a photographer, I want AI to interpret my creative brief so that selection uses more than generic technical quality.

## Acceptance criteria

- Invoke a genuine generative text or multimodal model.
- Ground the request in the brief and image-derived evidence.
- Validate structured output and allowed photo IDs.
- A failed call cannot masquerade as success.
- Valid guidance affects selection or an auditable downstream criterion.

## Tests written first

- Valid structured response; malformed output; invented photo ID; timeout/fallback.
- Controlled case showing model guidance affects ranking.

---

# A-05 — Pairwise feedback

**Depends on:** A-01 (#1), A-03 (#3)<br>
**Unlocks:** A-06 (#6)

## User story

As a photographer, I want to choose between A and B so that SelectIQ learns my preferences.

## Acceptance criteria

- Present two distinct photos from the current project.
- Record the winner and keep the losing photo eligible.
- Prevent exact repeated pairs within a session.
- Complete a limited 5–10-choice Alpha flow; the demo uses 5.

## Tests written first

- Winner stored; invalid ID; same-ID pair; loser eligibility; duplicate-pair protection.

---

# A-06 — Preference update

**Depends on:** A-03 (#3), A-05 (#5)<br>
**Unlocks:** A-07 (#7)

## User story

As a photographer, I want my choices to affect rankings so that recommendations become personal.

## Acceptance criteria

- A saved choice changes preference scores predictably on controlled features.
- Results are reproducible with a fixed seed.
- Preferences never leak across projects.
- Do not claim sophisticated active learning if the implementation is a heuristic or simple ranker.

## Tests written first

- Synthetic known-preference case; before/after score; zero choices; conflicting choices; project isolation.

---

# A-07 — Proposal generation

**Depends on:** A-02 (#2), A-03 (#3), A-04 (#4), A-06 (#6)<br>
**Unlocks:** A-08 (#8)

## User story

As a photographer, I want a small curated collection so that I can review the strongest candidates.

## Acceptance criteria

- Return exactly K distinct, valid photo IDs.
- Use prompt, genuine AI guidance, and saved-choice signals.
- Produce deterministic results for fixed inputs.
- A photo is not automatically eliminated solely because it lost a comparison.

## Tests written first

- Exact K; uniqueness; allowed IDs; ranking sensitivity; targets 1 and N; loser eligibility.
- Typical demo target: 5 selected from 15–20 photos.

---

# A-08 — Review and export

**Depends on:** A-07 (#7)<br>
**Unlocks:** A-09 (#9)

## User story

As a photographer, I want to remove suggestions and export filenames so that I control my final selection.

## Acceptance criteria

- Display the proposal in a grid.
- Removal reduces the count without adding a replacement.
- Export CSV contains only remaining original filenames.
- Duplicate filenames remain distinguishable and source files remain unchanged.

## Tests written first

- Remove one; remove all; exact CSV; no unseen photo; duplicate filename identity; unchanged source hashes.

---

# A-09 — End-to-end demo

**Depends on:** A-01 through A-08 (#1–#8)<br>
**Unlocks:** A-10 (#10)

## User story

As a test participant, I want a complete guided flow so that I can evaluate SelectIQ.

## Acceptance criteria

- Upload → brief/target → 5 A/B choices → genuine AI-informed proposal → remove → export works locally on the target Mac.
- Errors are informative and no mocked AI is represented as real.
- The seeded demo is reproducible.

## Tests written first

- End-to-end happy path; failure-path smoke test; fixed-seed reproducibility.

---

# A-10 — Satisfaction collection

**Depends on:** A-09 (#9)<br>
**Unlocks:** None

## User story

As a participating photographer, I want to rate the output so that the team can evaluate usefulness.

## Acceptance criteria

- Store a 1–5 rating and optional comment for the correct completed project.
- Reject invalid ratings.
- Do not invent participants, ratings, or validation evidence.

## Tests written first

- Valid rating; out-of-range rating; optional text; correct project linkage.

---

# Alpha definition of done

- A real tester completes upload → prompt → A/B → AI-assisted recommendation → remove → export.
- AI is genuinely executed and its contribution is traceable.
- Every issue has acceptance criteria and red/green test evidence or is openly marked incomplete.
- Validation uses permissioned photos and honest participant evidence.
- The narrow live demo is reliable on the target Apple Silicon Mac.

# Explicit Beta/later scope

- Approximately 300 inputs and 80 outputs.
- 20–40 adaptive comparisons and research-grade preference learning.
- Advanced uncertainty queues, calibrated confidence, and collection-level optimization.
- Docker/PostgreSQL, cloud infrastructure, accounts, RAW/HEIC, and deployment hardening.
