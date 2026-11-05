# SelectIQ Alpha - Part 1 Written Document

**Measurement date:** November 5, 2026  
**Repository:** https://github.com/EshaanShah/Select_IQ  
**Submission contents:** MVP hypothesis validation and Alpha user stories with acceptance criteria

## 1. Validation participants, data sources, and scope

### People and identifiers

The supplied validation evidence describes an **internal validation exercise**, not external participant outreach. The project-team identifiers associated with the repository are:

- **Eshaan Shah** - SelectIQ project team and repository owner; supplied the locally stored test galleries referenced in the validation summary.
- **Hani Moudarres** - SelectIQ project team and repository contributor.
- **Paul Lee** - SelectIQ project team and repository contributor.

No separate external photographer names, contact identifiers, or per-session participant assignments were recorded in the evidence supplied for this document. Accordingly, this report does not claim that external photographers were recruited or interviewed. The six galleries are data sources, not six human participants.

### Validation data and procedure

- Six real studio galleries stored locally on the project team's hard drives were used as the source data.
- The source galleries contained approximately 200-500 JPEG photographs each.
- Because of Alpha compute latency, active evaluation used 30-photo batches sampled from those galleries rather than processing each complete gallery in one run.
- The team completed 12 timed manual-versus-SelectIQ sessions.
- A manual cull provided a reference selection. SelectIQ results were compared with that reference for essential-photo recall and selection similarity.
- The team also compared brief-aware and personalized ranking with a generic ranking baseline.
- Only aggregated results are reported. Client identities, raw private galleries, and personally identifying information are not included in the repository or this submission.

## 2. Validation metrics, results, and decisions

| KPI / metric | Predeclared target | Observed result | Outcome |
|---|---:|---:|---|
| Total culling-time reduction | At least 40% versus manual culling | 33% | Target not met. Compute latency remained a material limitation. |
| Essential-photo recall | At least 90% against the hidden manual reference | 92% | Target met. The core selection-quality result was validated. |
| Keep + Review queue size | No more than 50% of the gallery | The supplied summary does not include the measured percentage | Not verifiable from the supplied evidence; no value is invented. |
| Brief-aware and personalized ranking | Outperform generic ranking on unseen photo groups | Brief-aware ranking outperformed the generic baseline | Directional target met; the supplied summary does not include an effect size. |
| AI/manual selection similarity | Supplementary comparison; no predeclared threshold supplied | 90% similarity between the AI proposal and the prior manual cull | Supports selection agreement, but does not replace recall, speed, or queue-size metrics. |
| Validation execution | Complete the planned timed comparisons | 12 sessions across six source galleries | Completed at the constrained 30-photo batch scope. |

### Decision

**SelectIQ achieved conditional validation.** The Alpha validated the core selection-quality hypothesis: essential-photo recall reached 92%, above the 90% target, and brief-aware ranking outperformed the generic baseline. It did not fully validate the original performance-and-scale hypothesis because time savings reached 33%, below the 40% target, and compute latency limited active testing to 30-photo batches.

The team therefore made a limited scope pivot: optimize batch throughput and repeat timed validation on complete 200-500-photo galleries before claiming production-scale validation. Beta must also report the Keep + Review percentage explicitly rather than leaving the queue guardrail unresolved.

## 3. Core Alpha user stories and acceptance criteria

### A-01 - Gallery upload

**User story:** As a photographer, I want to upload JPEGs so that SelectIQ can analyze my gallery.

**Acceptance criteria:**

- Accept 10-30 JPG/JPEG files for the Alpha workflow.
- Reject invalid formats and corrupt files with clear errors.
- Assign unique internal IDs while preserving original filenames.
- Ensure duplicate filenames do not overwrite one another.
- Display the accepted count and never modify source files.

### A-02 - Prompt and target

**User story:** As a photographer, I want to describe my story and set a target so that recommendations reflect my intent.

**Acceptance criteria:**

- Store a nonempty free-text creative brief.
- Store an integer target from 1 through the accepted-photo count.
- Reject blank prompts and invalid targets with clear errors.
- Reload the prompt and target from the local project session.

### A-03 - AI feature extraction

**User story:** As a photographer, I want images analyzed so that the product can compare visual content.

**Acceptance criteria:**

- Give every accepted photo a cached embedding from a real pretrained vision-language model.
- Give the prompt a compatible representation used for prompt-image relevance.
- Reuse cached embeddings during reanalysis.
- Surface analysis failures and never present them as successful inference.

### A-04 - LLM-guided brief interpretation

**User story:** As a photographer, I want AI to interpret my creative brief so that selection uses more than generic technical quality.

**Acceptance criteria:**

- Invoke a genuine generative text or multimodal model.
- Ground the request in the brief and image-derived evidence.
- Validate structured output and allowed photo IDs.
- Ensure a failed call cannot masquerade as success.
- Ensure valid guidance affects selection or an auditable downstream criterion.

### A-05 - Pairwise feedback

**User story:** As a photographer, I want to choose between A and B so that SelectIQ learns my preferences.

**Acceptance criteria:**

- Present two distinct photos from the current project.
- Record the winner and keep the losing photo eligible.
- Prevent exact repeated pairs within a session.
- Complete a limited 5-10-choice Alpha flow; the demo uses five choices.

### A-06 - Preference update

**User story:** As a photographer, I want my choices to affect rankings so that recommendations become personal.

**Acceptance criteria:**

- Make a saved choice change preference scores predictably on controlled features.
- Produce reproducible results with a fixed seed.
- Prevent preferences from leaking across projects.
- Do not claim sophisticated active learning if the implementation is a heuristic or simple ranker.

### A-07 - Proposal generation

**User story:** As a photographer, I want a small curated collection so that I can review the strongest candidates.

**Acceptance criteria:**

- Return exactly K distinct, valid photo IDs.
- Use the prompt, genuine AI guidance, and saved-choice signals.
- Produce deterministic results for fixed inputs.
- Do not automatically eliminate a photo solely because it lost a comparison.

### A-08 - Review and export

**User story:** As a photographer, I want to remove suggestions and export filenames so that I control my final selection.

**Acceptance criteria:**

- Display the proposal in a grid.
- Make removal reduce the count without adding a replacement.
- Export a CSV containing only the remaining original filenames.
- Keep duplicate filenames distinguishable and source files unchanged.

### A-09 - End-to-end demo

**User story:** As a test participant, I want a complete guided flow so that I can evaluate SelectIQ.

**Acceptance criteria:**

- Make upload, brief/target, five A/B choices, genuine AI-informed proposal, removal, and export work locally on the target Mac.
- Provide informative errors and never represent mocked AI as real.
- Make the seeded demo reproducible.

### A-10 - Satisfaction collection

**User story:** As a participating photographer, I want to rate the output so that the team can evaluate usefulness.

**Acceptance criteria:**

- Store a 1-5 rating and optional comment for the correct completed project.
- Reject invalid ratings.
- Do not invent participants, ratings, or validation evidence.

## 4. Summary

The Alpha demonstrated that SelectIQ can preserve essential photographs and produce selections closely aligned with a prior manual cull. The evidence supports the selection-quality hypothesis at a constrained 30-photo batch scope. The evidence does not yet support the original speed or full-gallery-scale hypothesis. Beta validation must improve throughput, test complete galleries, record the queue guardrail, and maintain clear participant and session-level evidence.
