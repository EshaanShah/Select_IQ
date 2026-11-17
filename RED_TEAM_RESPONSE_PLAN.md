# SelectIQ Red-Team Response Outline

## Overall priority

The highest-priority issue is scaling gallery-aware Groq interpretation beyond the current 10–30-photo Alpha. The present workflow uses at most three contact sheets with 12 photos each, so raising only the gallery limit would cause interpretation to fail above 36 photos. This has a low probability during the current Alpha because the app prevents larger galleries, but a high probability and high business impact for the planned 300-photo Beta.

Our proposed remediation is to generate one global rubric from the creative brief, score all photographs locally with OpenCLIP, group exact duplicates and visually similar photos, and place related photos in the same Groq review batch whenever possible. Each batch will use the same rubric and return only bounded photo-specific notes. SelectIQ will combine that evidence locally into one deterministic ranking rather than merging separate batch rankings. We will first benchmark the current pipeline at 37, 100, and 300 photos. If reviewing every batch is too slow or expensive, we will send Groq a diverse shortlist while keeping every photo locally scored and available for review.

## Finding-response table

| # | Red-team issue | Probability | Business impact | Plan to address it |
|---|---|---|---|---|
| 1 | The product is limited to approximately 30 photos, while realistic professional galleries may contain hundreds or thousands. | Low during Alpha; high for Beta | High | Increase limits only after staged benchmarks. Process photos incrementally, monitor memory/disk/runtime, and define supported gallery sizes through measured performance rather than an arbitrary number. |
| 2 | Gallery-aware Groq interpretation fails above 36 photos. | Certain if the gallery limit is raised without other changes | High | Generate one project-wide rubric, cluster similar photos, and review groups of up to 36 against that fixed rubric. Persist each completed batch, retry only failed batches, and combine all evidence locally. |
| 3 | Multiple Groq batches may apply inconsistent standards. | Medium | High | Generate and version the rubric once. Batch calls may add only schema-limited photo notes against that rubric; they may not redefine the brief or independently rank their batch. |
| 4 | Similar or near-duplicate photos may be separated across batches and never directly compared. | High in burst-heavy galleries | High for curation quality | Detect exact duplicates with content hashes and group near-duplicates using embeddings, perceptual similarity, and capture-time proximity. Keep cluster members in the same batch where possible and preserve manual cluster expansion. |
| 5 | A later Groq batch may fail after earlier batches succeed. | Medium | Medium–High | Store batch status and results transactionally. Retry only the failed batch, preserve completed work, display batch progress, and label the project as partially reviewed until required batches finish. |
| 6 | The current 20-call per-project safety limit may block larger galleries. | Low at 300 photos; high near 1,000 with full review | Medium | Calculate a project budget from one rubric call, expected review batches, and a bounded retry allowance. Retain an absolute ceiling to prevent loops. Switch to shortlist review when full review would exceed the budget. |
| 7 | Reviewing every photo with Groq may become too slow or expensive. | Medium | Medium–High | Measure tokens, latency, errors, and proposal quality during the 37/100/300-photo benchmarks. If necessary, use OpenCLIP scores, cluster coverage, uncertain cutoff cases, and preference-sensitive photos to create a generous shortlist. Do not delete or permanently exclude non-shortlisted photos. |
| 8 | Shortlisting may omit the photograph a human would prefer. | Medium if shortlist mode is used | High for result quality | Use a high-recall union of top-relevance photos, cluster representatives, uncertain candidates, and preference-sensitive photos. Keep Groq adjustments bounded and allow users to request deeper review or manually restore any photo. |
| 9 | Uploading 560 photos causes excess files to be read and decoded before rejection. | High when an oversized selection is submitted | Medium | Check remaining project capacity before reading excess streams. Warn or trim in the frontend and enforce the limit again on the backend. Return a summarized capacity error rather than hundreds of repeated errors. |
| 10 | A one-photo project can run full analysis even though no selection is required. | Low in intended Alpha use; possible through edge paths | Low–Medium | Enforce the minimum supported gallery before analysis or return the sole photo without ranking. Clearly label that no AI selection was required. |
| 11 | A project with 30 photos and target 30 runs analysis even though every photo must be returned. | Medium | Low–Medium | Warn that no culling will occur, then bypass ranking and provider calls. Return all eligible photos with provenance stating that selection was unnecessary. |
| 12 | Blank, punctuation-only, repeated-character, or extremely long briefs can reach the models. | Medium | Medium | Add minimum trimmed content, a maximum character/byte length, and punctuation-only validation. Warn about low-information input rather than attempting a language-biased “real word” rule. Prevent silent truncation. |
| 13 | A brief may describe content that does not appear in the gallery. | Medium | Medium | Research and calibrate a low-match warning using real galleries. Present it as guidance, allow the photographer to continue, and avoid treating an uncalibrated similarity threshold as objective truth. |
| 14 | Folder upload reportedly failed. | Unknown and potentially browser-specific | High if it blocks import | Reproduce the report in the same browser and environment. Retain multi-file selection as a fallback and add cross-browser folder-import checks. |
| 15 | Photo preview reportedly could not be closed. | Low | Low–Medium | Ensure Close and backdrop controls remain visible at all viewport sizes. Add Escape-to-close, focus trapping, and focus restoration for keyboard accessibility. |
| 16 | Input boundaries for gallery size, targets, and files may be incomplete. | Medium for unusual inputs | Medium | Keep strict target validation and add early gallery-readiness checks. Continue rejecting corrupt, oversized, non-JPEG, and excessive-pixel files. Add explicit rules for when a gallery is ready for analysis. |
| 17 | Groq guidance may not measurably improve the final selection. | Medium | High for the value proposition | Compare OpenCLIP-only, OpenCLIP-plus-Groq, and full preference-informed proposals using real galleries and blinded human review. Use satisfaction, human-cull overlap, preference rate, and failure rate as evaluation metrics. |
| 18 | Repeated pairs, invalid winners, or foreign-project photos could corrupt pairwise feedback. | Low with current controls | Medium–High if validation regresses | Preserve strict project, pair, winner, duplicate-pair, and comparison-budget validation. Keep losing photos eligible for the final proposal. Include these rules in the acceptance-criteria checklist. |
| 19 | Pairwise preference results may be inconsistent. | Low for stored evidence; medium across fresh model evidence | Medium | Store model version, seed, feature version, choices, and interpretation version. Reuse stored evidence rather than silently regenerating it. Clarify that application ranking is deterministic once evidence is fixed. |
| 20 | The proposal may not contain exactly K distinct photos or may not be reproducible. | Low with the current deterministic curator | High if it occurs | Preserve unique-ID checks, exactly-K validation, normalized scoring, stable sorting, and deterministic tie-breaking. Treat any violation as a release-blocking regression. |
| 21 | CSV export reportedly failed, blocking the user’s final deliverable. | Unknown | High | Reproduce the exact browser and environment failure. Improve visible download errors and retain filename/row validation. Provide a clear retry path if export generation or download fails. |
| 22 | Starting a new cull appears to erase the previous project. | High as a user-perception problem | Medium–High | Add a project-history screen with reopen, rename, and explicit delete actions. “Start new” should only switch the active project; deletion must require separate confirmation. |
| 23 | The end-to-end workflow may be blocked when export or another final step fails. | Medium | High | Treat upload, analysis, comparison, proposal, review, export, and feedback as one release workflow. Show recoverable errors at each stage and retain completed project state during retry. |
| 24 | Satisfaction feedback may be missing or unreliable. | Low with the current feature | Medium | Preserve strict 1–5 validation, optional comments, completed-project requirements, project isolation, and duplicate-submission protection. Add reporting later so feedback informs model and workflow decisions. |
| 25 | External API timeouts, throttling, outages, or malformed responses can interrupt analysis. | Medium | Medium–High | Preserve explicit failure states, strict schema parsing, photo-label allow-lists, bounded retries, and retry controls. For multi-batch processing, checkpoint each batch and respect provider rate limits. |
| 26 | A fallback might be mistaken for successful Groq guidance. | Low with current provenance; high if labeling regresses | High | Always distinguish complete Groq guidance, partial Groq review, OpenCLIP-only fallback, and deterministic test signals. Never label partial or failed interpretation as complete success. |
| 27 | Image payloads may become too large or lose useful visual detail. | Medium as gallery size grows | Medium–High | Keep standard thumbnail dimensions and a bounded number of photos per sheet. Measure payload bytes, image tokens, label readability, and the ability to distinguish near-duplicates before increasing sheet density. |
| 28 | Sending contact sheets to Groq creates a privacy boundary. | Medium whenever live Groq is enabled | High for sensitive galleries | Tell users that labeled contact sheets leave the machine, require permissioned galleries, and offer a local/brief-only mode. Never send original full-resolution files unless explicitly designed and disclosed. |
| 29 | Large galleries may overwhelm the browser even if backend analysis succeeds. | Medium at 300; high at thousands | Medium–High | Add lazy thumbnail loading, a virtualized grid, pagination/filtering, and bounded client state. Avoid rendering every full card simultaneously. |
| 30 | Large projects may consume excessive local disk space. | Medium | Medium | Measure storage amplification, reuse content hashes and cached embeddings, add explicit project/cache cleanup, and evaluate safe local references or hard links without modifying originals. |
| 31 | Long-running analysis may be lost if the process or browser stops. | Medium for large galleries | High | Add persistent job stages, progress, cancellation, restart, and resume. Commit completed embeddings and batch results incrementally so successful work is not repeated. |
| 32 | SQLite or the current worker design may become a bottleneck. | Low for a local 300-photo project; higher for concurrent or hosted use | Medium–High later | Benchmark before introducing new infrastructure. Add bounded concurrency and durable local job state first. Revisit the database and queue only when measured contention or deployment requirements justify it. |
| 33 | API credentials could leak as the system evolves. | Low with current server-side configuration | High | Keep credentials in ignored environment files, never include them in frontend bundles or logs, add secret scanning, and rotate any exposed key immediately. |
| 34 | Test coverage may be difficult for reviewers to map to user stories. | High as a documentation problem | Medium | Create a concise A-01–A-10 map connecting acceptance criteria to automated and manual checks. Maintain it as part of each issue’s completion criteria. |

## Prioritized implementation outline

### Immediate: validation and clarity

1. Reject excess uploads before reading or decoding them.
2. Add objective brief-length and punctuation-only rules.
3. Define minimum gallery readiness.
4. Skip ranking when target equals eligible photo count.
5. Improve preview accessibility and error messages.
6. Make model/fallback provenance unmistakable.

### Next: measure larger galleries

1. Parameterize limits on an experimental branch.
2. Test 37-, 100-, and 300-photo galleries.
3. Measure runtime, memory, disk, browser responsiveness, Groq calls, tokens, latency, and failures.
4. Compare full multi-batch review with shortlist review.

### Beta: cluster-aware multi-batch review

1. Generate one fixed global rubric from the brief.
2. Score every photo locally with OpenCLIP.
3. Group exact duplicates and near-duplicates.
4. Keep similar photos in the same batch where possible.
5. Request only bounded photo-specific notes from each batch.
6. Persist batch progress and retry only failed work.
7. Combine all evidence into one deterministic global ranking.
8. Use shortlist mode if full review exceeds resource or call budgets.

### Product hardening

1. Add project history and explicit deletion.
2. Virtualize the large-gallery interface.
3. Add resumable background processing and cleanup.
4. Evaluate real-model usefulness with photographers.
5. Reassess storage, database, and worker architecture from benchmark results.

## How SelectIQ works now and how the remediation changes it

### Current SelectIQ architecture

The current Alpha is designed for one local project containing 10–30 JPEG photographs. Its selection flow is:

```text
Upload gallery
    ↓
Save creative brief and target K
    ↓
OpenCLIP creates one embedding for every photo
    ↓
OpenCLIP embeds the original brief and calculates prompt relevance
    ↓
SelectIQ creates up to three contact sheets with 12 photos each
    ↓
One Groq call receives the brief, target, CLIP relevance, and all contact sheets
    ↓
Groq returns a summary, one set of favor/avoid descriptors, and optional photo notes
    ↓
OpenCLIP embeds the descriptors and calculates a guided score for every photo
    ↓
The photographer completes five A/B choices
    ↓
The preference model scores every photo from those choices
    ↓
SelectIQ combines prompt relevance, Groq guidance, and preference scores
    ↓
Deterministic top-K proposal
```

OpenCLIP and Groq perform different jobs. OpenCLIP runs locally and places images and text in a shared numerical embedding space. This lets SelectIQ calculate how closely each photo matches the original brief and Groq’s descriptors. Groq interprets the photographer’s open-ended intent and visually examines the contact sheets. It returns general concepts to favor or avoid and may add a small bounded boost or penalty to a labeled photo.

Groq does not directly choose the final gallery. SelectIQ calculates the final scores locally, normalizes the available signals, and selects the highest-ranked K distinct photos with stable tie-breaking.

The scalability problem comes from asking the single Groq call to see the complete gallery. The implementation allows three contact sheets with 12 photos on each sheet, so gallery-aware interpretation has a 36-photo ceiling. Making each thumbnail much smaller would reduce Groq’s ability to distinguish composition, expression, focus, and other subtle differences. Making the sheets much larger would increase payload size, image-token use, latency, and provider-limit risk.

### Remediated architecture for larger galleries

The proposed architecture separates interpreting the brief from visually reviewing individual photos:

```text
Upload a larger gallery incrementally
    ↓
First Groq call: creative brief → one fixed global rubric
    ↓
OpenCLIP embeds the rubric and every photo locally
    ↓
SelectIQ scores every photo against the same rubric
    ↓
Exact duplicates and visually similar photos are grouped
    ↓
Clusters are assigned to review batches of no more than 36 photos
    ↓
Each batch is sent to Groq with the same fixed rubric
    ↓
Groq returns only bounded photo-specific notes for that batch
    ↓
SelectIQ combines all local scores and batch notes globally
    ↓
Pairwise preferences are applied across the complete project
    ↓
One deterministic top-K proposal is produced
```

#### Decision 1: Use the first Groq call only to establish the global rubric

The first call converts the creative brief into one versioned set of positive descriptors, negative descriptors, and editorial priorities. For example, it might favor “misty mountain scale” and “people exploring wilderness” while avoiding “crowded indoor scenes.”

**Why:** If every photo batch independently interprets the brief, batch one could favor dramatic color while batch two favors subdued color. One fixed rubric prevents that drift and gives all photos the same editorial standard.

#### Decision 2: Use OpenCLIP to score the entire gallery locally

OpenCLIP creates embeddings for every photo and for the fixed rubric. Cosine similarity then gives every photo globally comparable prompt and guidance scores.

**Why:** OpenCLIP inference is batchable, cacheable, and does not require sending every original photo to an external provider. Its work grows with gallery size, but it is primarily a local processing-time problem rather than a hard 36-photo boundary. It also creates one common scoring space across every Groq batch.

#### Decision 3: Group similar photos before creating Groq batches

SelectIQ will first identify exact duplicates using content hashes. Near-duplicates and visually related photos can be grouped using OpenCLIP similarity, perceptual similarity, and capture-time proximity. Batch construction will keep members of the same cluster together whenever possible.

**Why:** If two nearly identical frames are placed in different batches, Groq cannot directly compare their composition, expression, lighting, or focus. Keeping them together gives the model the context needed to say which version is stronger. Clustering also stops one burst from dominating the final proposal.

Clustering will organize photographs, not delete them. Every original remains locally scored, stored, and available for manual review. If a cluster is too large for one batch, representative images can be reviewed first while the full cluster remains expandable.

#### Decision 4: Review multiple standard-size contact-sheet batches

Each batch will contain no more than the visually tested contact-sheet capacity, initially 36 photos. For 300 photos, full review would require approximately nine photo-review calls plus the initial rubric call.

Every batch receives the same rubric and is asked only for bounded photo-specific notes, such as a small boost for a strong match or penalty for a clear conflict. A batch does not create its own final ranking.

**Why:** Standard-size thumbnails preserve visual detail better than placing hundreds of tiny images on one sheet. Using the same rubric and bounded note values makes evidence from separate batches compatible. SelectIQ merges the evidence locally rather than trying to combine unrelated batch winner lists.

#### Decision 5: Persist each batch independently

The application will record which batches are queued, running, completed, or failed, along with their returned evidence.

**Why:** A 300-photo review may take several API calls. If batch six fails, batches one through five should not be repeated. Checkpointing reduces cost, supports retry and resume, and lets the UI show accurate progress. Until all required batches finish, the proposal must be labeled as partially reviewed rather than fully Groq-guided.

#### Decision 6: Keep final ranking local and deterministic

After all available evidence is collected, SelectIQ applies the same scoring rules across the complete gallery. Pairwise preferences also score the full project rather than one batch. Stable sorting and tie-breaking produce exactly K distinct photos.

**Why:** Groq batches cannot reliably compare photos that appear in different requests. Local global scoring solves that problem. Given the same stored rubric, embeddings, batch notes, choices, and target, the final proposal remains reproducible even though a fresh external model call may vary.

#### Decision 7: Use a shortlist only if full review is impractical

The first experiment will measure full batch review at 37, 100, and 300 photos. If tokens, latency, call budgets, or rate limits make full review impractical, SelectIQ can construct a generous shortlist from:

- The strongest locally relevant photos
- Representatives from uncovered similarity clusters
- Photos near the likely selection cutoff
- Photos most affected by pairwise preferences

**Why:** This keeps Groq usage bounded while maintaining high recall and visual diversity. Non-shortlisted photos are not removed: they retain local scores, remain eligible for ranking, and stay available for manual review. Groq’s photo-specific adjustment remains small enough that a strong unreviewed photo can still be selected.

### Summary of the architectural difference

| Current Alpha | Remediated larger-gallery design |
|---|---|
| One Groq call interprets the brief and sees the entire gallery | One Groq call establishes the rubric; later calls review bounded photo batches |
| Up to three contact sheets represent all photos | Any number of checkpointed batches can represent the gallery within a calculated call budget |
| All photos must fit within 36 contact-sheet positions | Local OpenCLIP scores every photo regardless of Groq batch count |
| Similar photos may be separated arbitrarily | Similar photos are clustered and kept together where possible |
| One request either completes or loses gallery-specific guidance | Completed batches are saved and only failed batches are retried |
| Appropriate for the 10–30-photo Alpha | Designed to be measured first at 37, 100, and 300 photos |
| Final ranking is deterministic | Final ranking remains deterministic because all evidence is combined locally |

## Two-minute presentation focus

The largest problem is that gallery-aware Groq interpretation currently stops above 36 photographs because SelectIQ uses at most three 12-photo contact sheets. The problem is contained by the 10–30-photo Alpha, but it prevents a direct move to the planned 300-photo Beta. Our first step is to benchmark the current local pipeline at 37, 100, and 300 photos instead of assuming a complete rewrite. Our proposed scalable design creates one global rubric from the brief, scores every photo locally with OpenCLIP, groups similar photographs so they remain together, and reviews standard-size batches against the same rubric. The system will combine globally comparable evidence rather than separate batch rankings, preserve completed batches during retries, and clearly label partial failures. If full batch review is too costly, we will use a diverse shortlist while keeping every photo locally scored and manually available.
