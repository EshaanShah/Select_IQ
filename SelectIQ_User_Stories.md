# SelectIQ Alpha — Finalized User Stories

**Version:** 1.1<br>
**Status:** Finalized for Alpha implementation<br>
**Source of truth:** SelectIQ PRD v1.2<br>
**Method:** Each story is implemented with test-driven development: write the listed tests, confirm meaningful failure, implement the minimum behavior, and refactor only while the tests remain green.

---

# 1. Alpha Scope and Issue Conventions

These ten user stories cover the complete Alpha workflow:

**Import JPEG gallery → describe creative intent → choose target count → analyze contextually → complete adaptive comparisons → receive target-sized proposal → review uncertainty → remove photographs → export filenames → submit evaluation.**

Suggested GitHub labels:

- `type:user-story`
- `priority:p0` or `priority:p1`
- `area:ingestion`
- `area:ai`
- `area:preference-learning`
- `area:curation`
- `area:review`
- `area:evaluation`
- `tdd:red`
- `tdd:green`

Every issue is complete only when:

- Its acceptance criteria are satisfied.
- Its automated tests were written before production implementation.
- The tests were observed failing for the intended reason.
- The complete relevant test suite passes.
- No original photograph is modified or deleted.
- Any material limitation is documented.

---

# US-01 — Import and validate a local JPEG gallery

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:ingestion`, `priority:p0`<br>
**Dependencies:** None<br>
**PRD traceability:** FR-01, AC-01

## User story

As a photographer, I want to import a local gallery of JPEG photographs so that SelectIQ can prepare the photographs for curation without changing my originals.

## Acceptance criteria

- The photographer can select and submit a gallery of JPEG/JPG files.
- The system supports approximately 300 valid photographs in one project.
- Each accepted photograph receives a unique internal ID while retaining its original filename.
- Duplicate filenames do not overwrite one another.
- Unsupported or undecodable files are rejected with understandable errors.
- One invalid file does not prevent other valid files from being accepted.
- The accepted-photo count is displayed before analysis begins.
- Original user files are never modified or deleted.

## Tests written first

- Importing a valid JPEG creates one accepted photo record with the correct filename.
- Importing approximately 300 valid JPEGs accounts for every file.
- A permissioned sports fixture gallery and a permissioned retirement fixture gallery are both accepted without scenario-specific ingestion failures.
- Two files with the same filename receive different internal IDs and storage locations.
- An unsupported file is rejected with a defined error.
- A corrupt JPEG is rejected without terminating the gallery import.
- Imported source fixtures retain their original hashes after processing.

---

# US-02 — Describe creative intent, including contextual technical preferences

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:ai`, `priority:p0`<br>
**Dependencies:** US-01<br>
**PRD traceability:** FR-02, FR-09, AC-02, AC-04A

## User story

As a photographer, I want to describe the story and aesthetic I want in natural language so that SelectIQ evaluates photographs according to my intent instead of a generic definition of a good photograph.

## Acceptance criteria

- The photographer can submit an unrestricted free-text creative brief.
- The original brief is preserved and associated with the current project.
- The system derives usable evidence for positive, negative, neutral, and context-specific preferences.
- The brief may describe mood, subject, emotion, composition, storytelling, or technical characteristics.
- A technical preference can be contextual, such as accepting motion blur for dancing while preferring sharp formal portraits.
- Explicit instructions can reduce, remove, or reverse a generic technical-quality penalty in the relevant context.
- A contextual preference is not applied to unrelated photographs or moments.
- Failure to interpret part of a brief does not silently replace the original text or invent a preference.

## Tests written first

- “Prioritize candid emotion” produces positive evidence for candid emotional moments.
- “Avoid overly posed portraits” produces negative evidence for posed portraiture.
- “Avoid blurry photographs” produces a negative blur preference.
- “Keep expressive motion blur on the dance floor” produces a positive, dance-context blur preference.
- “Sharp formal portraits, but energetic dance photographs may be blurry” produces two distinct context rules.
- A sports brief such as “prioritize peak action, athlete emotion, and energetic panning blur” produces positive, sports-context evidence.
- A retirement brief such as “prioritize the retiree’s relationships, speeches, embraces, and respectful group portraits” produces distinct retirement-context evidence.
- The dance-floor blur preference does not reward missed focus in a formal portrait fixture.
- Malformed AI output is rejected or converted to a safe validated fallback without changing the original brief.

---

# US-03 — Set the requested collection size

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:curation`, `priority:p0`<br>
**Dependencies:** US-01<br>
**PRD traceability:** FR-03, AC-03

## User story

As a photographer, I want to specify the number of photographs in the proposed collection so that the recommendation fits the needs of my project.

## Acceptance criteria

- The photographer can enter a positive whole-number target.
- The target is stored with the current project.
- Zero, negative, fractional, and nonnumeric targets are rejected.
- A target greater than the number of accepted photographs is rejected.
- The photographer receives a clear explanation when the target is invalid.
- Manual removal during final review may reduce the collection below this initial target.

## Tests written first

- A target of 80 is accepted for a 300-photo gallery.
- Zero and negative values are rejected.
- Fractional and nonnumeric values are rejected.
- A target of 301 is rejected for a 300-photo gallery.
- The accepted target remains associated with the correct project.

---

# US-04 — Analyze photographs without enforcing generic technical taste

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:ai`, `priority:p0`<br>
**Dependencies:** US-01, US-02<br>
**PRD traceability:** FR-04, AC-04, AC-04A

## User story

As a photographer, I want SelectIQ to treat technical characteristics in the context of my creative intent so that meaningful photographs are not discarded simply because they are blurry, grainy, unusually exposed, or technically unconventional.

## Acceptance criteria

- Every valid photograph receives the representations needed for similarity, comparison, and ranking.
- Sharpness, exposure, contrast, grain, and related measurements are stored as descriptive evidence rather than universal pass/fail judgments.
- No photograph is automatically excluded because one technical metric crosses a threshold.
- The analysis can distinguish, when evidence permits, likely accidental blur from story-supporting or intentional motion blur.
- Explicit brief preferences and repeated comparison choices can reduce, remove, or reverse default technical penalties.
- Technical overrides are scoped to the relevant context.
- A story-relevant blurry photograph can outrank a sharp but irrelevant photograph.
- When intentionality or value cannot be determined reliably, the photograph remains eligible and the ambiguity can contribute to an uncertainty flag.

## Tests written first

- A low sharpness measurement alone does not set a photograph to ineligible.
- With no contrary preference, an obvious accidental-blur fixture receives the documented default treatment.
- With a brief requesting expressive motion blur, a relevant motion-blur fixture is not suppressed by the default blur penalty.
- A relevant expressive-blur fixture outranks a sharp irrelevant fixture when the creative brief supports it.
- A dance-specific blur preference does not reverse the penalty for a missed-focus formal portrait.
- A sports panning-blur preference can preserve a peak-action frame without preserving an unrelated missed-focus frame.
- A retirement preference can preserve a grainy low-light embrace while still deprioritizing a blurred posed group portrait.
- An ambiguous blur case remains eligible and exposes an uncertainty reason.
- Analysis failure for one photograph does not terminate processing for the rest of the gallery.

---

# US-05 — Teach SelectIQ through adaptive A/B comparisons

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:preference-learning`, `priority:p0`<br>
**Dependencies:** US-02, US-04<br>
**PRD traceability:** FR-05 through FR-09, AC-05 through AC-07

## User story

As a photographer, I want to choose between strategically selected pairs of photographs so that SelectIQ can learn what I value for this specific gallery.

## Acceptance criteria

- Each comparison displays exactly two photographs from the current project.
- The photographer can choose photograph A or photograph B.
- The system records the pair, winner, loser, project, and sequence position correctly.
- The unselected photograph remains eligible for final inclusion.
- An optional predefined reason or custom explanation may be recorded.
- Skipping an explanation does not block progress.
- Later pairs are influenced by earlier choices rather than following an exclusively random fixed sequence.
- The strategy includes both broad-preference and subtle within-group comparisons.
- Repeated uninformative comparisons are avoided.
- The workflow ends after the configured comparison budget, normally approximately 20–40 choices.
- Preference learning is isolated to the current project.

## Tests written first

- Choosing A records A as winner and B as loser for the correct project.
- The losing photograph remains eligible.
- A comparison can be completed without a reason.
- A predefined or custom reason is stored when supplied.
- Reversing pair display order preserves equivalent preference evidence.
- A recorded choice changes at least one subsequent ranking or pair-selection decision in a controlled fixture.
- Sports comparisons include informative choices within burst sequences and between peak action, reaction, and contextual frames.
- Retirement comparisons include informative choices among speech, presentation, embrace, candid-reaction, and posed-group frames.
- A resolved pair is not immediately repeated without a documented reason.
- A new project begins with a separate preference-learning context.
- The configured comparison limit ends the learning phase even when uncertainty remains.

---

# US-06 — Generate a personalized, redundancy-aware proposal

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:curation`, `priority:p0`<br>
**Dependencies:** US-03, US-04, US-05<br>
**PRD traceability:** FR-10, AC-08

## User story

As a photographer, I want SelectIQ to propose a target-sized collection that reflects my preferences and intended story so that I receive a useful starting point rather than a generic quality ranking.

## Acceptance criteria

- The initial proposal contains exactly the requested number of unique photographs when enough valid photographs exist.
- Every recommendation belongs to the current uploaded project.
- Selection considers the creative brief, demonstrated preferences, contextual image value, similarity, redundancy, and collection contribution.
- Generic technical-quality assumptions do not override explicit or repeatedly demonstrated artistic preferences.
- A photograph that lost an A/B comparison remains eligible.
- Visually similar photographs are not automatically reduced to one photograph per group.
- Unnecessary repetition is limited while meaningful related photographs may coexist.
- There are no predetermined subject, mood, or moment quotas.
- Proposal generation validates IDs, uniqueness, count, and project ownership before displaying results.

## Tests written first

- A request for 80 produces 80 unique valid recommendations from a sufficient 300-photo fixture.
- A photograph from another project cannot enter the proposal.
- A previous A/B loser can be selected when it improves the collection.
- Near-duplicate evidence reduces unnecessary repetition without enforcing a one-per-group rule.
- Two related photographs can both be selected when each adds documented value.
- A sports proposal chooses meaningful frames from a burst while retaining distinct action, reaction, and storytelling photographs.
- A retirement proposal limits repetitive ceremony frames while retaining distinct relationships, milestones, portraits, and atmosphere.
- An explicit artistic preference can outweigh a generic technical metric.
- Identical stored inputs and deterministic configuration produce the same proposal.
- Invalid or incomplete output is rejected rather than presented as finished.

---

# US-07 — Review uncertain recommendations separately

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:review`, `area:ai`, `priority:p0`<br>
**Dependencies:** US-06<br>
**PRD traceability:** FR-11 through FR-13, AC-09

## User story

As a photographer, I want uncertain recommendations identified and explained so that I can focus my judgment where SelectIQ has weak or conflicting evidence.

## Acceptance criteria

- Uncertain recommendations appear in a distinct review group.
- Uncertain recommendations remain part of, not additions to, the requested proposal count.
- Uncertainty is distinguished from low aesthetic quality.
- Valid sources include weak preference evidence, conflicting signals, close alternatives, ambiguous redundancy, or unclear artistic versus accidental technical characteristics.
- Every uncertainty flag has a concise evidence-based explanation.
- Explanations for other recommendations are available on demand.
- The interface does not present heuristic uncertainty as a calibrated probability.
- Explanations do not invent unsupported technical facts.

## Tests written first

- An uncertain photograph is included in both the proposal total and uncertain subgroup without duplication.
- Weak or conflicting evidence produces a defined uncertainty reason.
- Ambiguous intentional-versus-accidental blur can produce an uncertainty reason.
- An ambiguous sports motion-blur frame and an ambiguous low-light retirement moment can be retained for uncertainty review instead of silently rejected.
- A confident recommendation is not placed in the uncertain subgroup.
- A gallery with no uncertain recommendations renders a valid empty state.
- Every explanation is associated with the correct photograph.
- Unsupported measurements are not included in an explanation.

---

# US-08 — Review and remove unwanted recommendations

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:review`, `priority:p0`<br>
**Dependencies:** US-06, US-07<br>
**PRD traceability:** FR-14, FR-15, AC-10, AC-11

## User story

As a photographer, I want to inspect the proposal and remove unwanted photographs so that I retain final creative control over the collection.

## Acceptance criteria

- The complete proposed collection is visible in a photo grid.
- A photograph can be inspected at a larger size.
- The photographer can remove any regular or uncertain recommendation.
- Removal decreases the selected count immediately.
- Removal does not insert a replacement.
- Removal does not trigger mandatory retraining.
- Removing a photograph leaves every other selected photograph unchanged.
- Removed recommendations are excluded from finalization.
- Original photograph files remain unchanged.
- Adding rejected candidates back into the collection is outside Alpha scope.

## Tests written first

- Removing five photographs from an 80-photo proposal produces 75 selections.
- No replacement appears after removal.
- Removing one photograph does not change the IDs of the remaining selection.
- A photograph can be removed from the uncertain subgroup.
- Repeating a removal request is handled safely and does not decrement twice.
- Source fixture hashes remain unchanged after review.

---

# US-09 — Export the final filename list

**Priority:** P0<br>
**Labels:** `type:user-story`, `area:review`, `priority:p0`<br>
**Dependencies:** US-08<br>
**PRD traceability:** FR-16, AC-12

## User story

As a photographer, I want to download the filenames of my remaining selections so that I can continue the workflow in my normal photography tools.

## Acceptance criteria

- The photographer can download a machine-readable or plain-text filename list.
- Every remaining selected photograph appears exactly once.
- Removed photographs do not appear.
- Original filenames and extensions are preserved.
- Duplicate filenames from different source paths remain distinguishable using documented export information.
- The export reflects the current reviewed state at the moment it is generated.
- Exporting does not copy, edit, or delete original image files.

## Tests written first

- Exporting 75 remaining selections produces 75 unique selection records.
- Removed filenames are absent.
- Spaces, punctuation, and Unicode characters are preserved safely.
- Duplicate base filenames are represented without ambiguity.
- A later removal is reflected in a newly generated export.
- No original image is modified during export.

---

# US-10 — Rate the proposed collection and provide optional feedback

**Priority:** P1<br>
**Labels:** `type:user-story`, `area:evaluation`, `priority:p1`<br>
**Dependencies:** US-06; normally completed after US-08 and US-09<br>
**PRD traceability:** FR-17, AC-13

## User story

As a participating photographer, I want to rate SelectIQ’s proposed collection and optionally explain my rating so that the team can evaluate whether the Alpha reflects photographers’ creative intent.

## Acceptance criteria

- The photographer can submit one overall satisfaction rating from 1 through 5.
- The scale labels range from very dissatisfied to very satisfied.
- Optional comments may be submitted with the rating.
- A rating outside the valid range is rejected.
- Feedback is associated with the correct project session.
- Operational metrics needed for the Alpha evaluation are retained, including uploaded count, comparisons completed, processing time, removals, export count, uncertain count, and failures.
- Evaluation storage does not alter the final selection.

## Tests written first

- Each integer rating from 1 through 5 is accepted.
- Ratings below 1, above 5, or nonintegral are rejected.
- A rating with no comment is accepted.
- A rating with a comment preserves that comment.
- Feedback is linked to the correct project.
- Evaluation metrics can be grouped by sports and retirement gallery scenario without mixing project-specific preferences.
- Submitting feedback does not change selected-photo IDs or export results.

---

# 2. Required Test Gallery Scenarios

The Alpha test suite must exercise the same kinds of photographs the product will actually curate. At minimum, maintain two permissioned fixture sets or equivalent annotated/synthetic representations.

## Sports fixture set

Include representative cases for:

- Peak action with visible game context.
- Athlete and team reactions before, during, and after action.
- Celebration, sideline, bench, crowd, and environmental storytelling.
- High-speed bursts containing near-duplicates with meaningful timing differences.
- Intentional panning or motion blur that communicates energy.
- Accidental missed focus, camera shake, obstruction, and empty-action frames.

Required behavioral checks:

- A relevant peak-action frame can outrank a technically cleaner frame with no meaningful action.
- A requested panning-blur aesthetic can override the default blur penalty only for relevant action photographs.
- Burst handling limits redundancy without automatically selecting only one frame.
- Reaction and context photographs remain eligible even when they are not the sharpest action frames.

## Retirement photoshoot fixture set

Include representative cases for:

- The retiree alone and with family, friends, and colleagues.
- Speeches, presentations, embraces, candid reactions, posed groups, details, and venue context.
- Repeated ceremony and group-photo sequences with subtle expression or eye-contact differences.
- Low-light emotional moments with grain, unusual exposure, or minor motion blur.
- Accidental missed focus and technically weak frames that do not add story value.

Required behavioral checks:

- An emotionally important low-light moment can outrank a technically cleaner but less relevant detail.
- A request for respectful, sharp group portraits does not inherit a blur preference from another context.
- Repetitive speech or presentation frames are reduced without removing distinct emotional beats.
- The final proposal represents the retiree’s relationships and milestone rather than optimizing only for generic aesthetics.

## Fixture privacy and provenance

- Use photographs supplied with permission for development and evaluation.
- Do not commit private participant galleries to the public repository without appropriate permission from the photographer and depicted subjects.
- Automated unit tests may use small derived images, annotations, or synthetic feature records when real photographs cannot be published.
- Record fixture provenance, permitted use, scenario, expected behavior, and any known limitations.
- Keep sports and retirement expectations project-specific; do not encode one genre’s aesthetic as a universal rule.

# 3. Traceability Check

The finalized stories cover every required Alpha capability:

| PRD capability | User story |
|---|---|
| JPEG gallery ingestion and validation | US-01 |
| Free-text creative direction | US-02 |
| Context-dependent technical preferences | US-02, US-04 |
| Target collection size | US-03 |
| Technical, semantic, and similarity analysis | US-04 |
| Adaptive comparison and project-specific learning | US-05 |
| Target-sized, redundancy-aware curation | US-06 |
| Uncertainty grouping and explanations | US-07 |
| Final human review and removal | US-08 |
| Filename export | US-09 |
| Satisfaction evaluation and metrics | US-10 |
| Sports and retirement fixture coverage | US-01, US-02, US-04 through US-07, US-10 |

No additional Alpha user story is required for blur specifically. Blur is a cross-cutting example of the broader context-aware technical-evidence requirement and is tested in US-02, US-04, US-06, and US-07.
