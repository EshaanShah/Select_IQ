# SelectIQ
## Product Requirements Document (PRD)

**Version:** 1.0  
**Status:** Product discovery complete — ready for technical architecture and feasibility planning  
**Product type:** AI-assisted, preference-learning photo culling application  
**Initial release:** Local research prototype (MVP)  
**Primary platform:** Web application running locally on an Apple Silicon Mac  
**Target users:** Independent photographers participating in controlled product evaluations

---

# 1. Executive Summary

SelectIQ is an AI-powered photo culling application that helps photographers transform large, uncurated galleries into smaller, personalized collections that reflect their creative vision.

A photographer uploads approximately 300 JPEG photographs, describes the story they want the images to convey, and specifies a desired final collection size, such as 80 photographs.

SelectIQ analyzes the gallery and conducts an interactive learning session consisting of approximately 20–40 adaptive pairwise comparisons. Each comparison asks the photographer to select their preferred photograph from two presented images. The photographer may optionally explain the preference using predefined reasons or custom text.

The system uses the creative brief, visual characteristics of the photographs, and the photographer's choices to progressively refine its understanding of what the photographer values.

After the comparison phase, SelectIQ proposes a curated gallery containing the requested number of photographs.

The proposed gallery should:

- Reflect the photographer's demonstrated preferences.
- Align with the creative direction described in the initial prompt, unless later choices indicate otherwise.
- Avoid unnecessary visual repetition.
- Preserve variety where it meaningfully improves the collection.
- Include potentially valuable photographs even when they lost individual comparisons.
- Identify recommendations where the system has insufficient confidence.

The photographer reviews the proposed gallery, removes unwanted photographs, and exports a list of selected filenames.

**The purpose of the MVP is to demonstrate that adaptive human feedback can improve AI-assisted photographic selection with a relatively small number of interactions.**

SelectIQ is not intended to replace the photographer's final creative judgment.

# 2. Problem Statement

Photographers frequently capture far more photographs than they ultimately deliver or use.

A single event may produce hundreds or thousands of photographs, many of which are technically acceptable but visually repetitive or less relevant to the intended story.

Traditional image culling involves repeatedly evaluating photographs for:

- Technical quality.
- Emotional expression.
- Composition.
- Subject matter.
- Creative relevance.
- Redundancy.
- Overall contribution to the collection.

The most difficult decisions are often subjective.

Two technically excellent photographs may differ in subtle but important ways. One may better capture the emotion of a moment, while another may have superior composition.

Existing automated approaches based primarily on technical quality or generic image aesthetics cannot necessarily capture what a specific photographer values for a particular project.

SelectIQ addresses this problem by combining image analysis with project-specific preference learning.

Instead of assuming that the same selection criteria work for every photographer, the application asks the photographer to demonstrate preferences through comparisons.

# 3. Product Vision

SelectIQ should function as an intelligent photography assistant that learns what matters to the photographer during a particular project.

Its defining capability is not merely identifying technically good photographs.

It is understanding which photographs best support the photographer's intended creative outcome.

### Product principle

**The photographer teaches SelectIQ what matters. SelectIQ uses that learning to propose a smaller, more relevant gallery.**

The system should require minimal instructions, make efficient use of human feedback, and communicate uncertainty when it cannot confidently distinguish between candidates.

The final output is always a recommendation that the photographer controls.

# 4. Goals and Success Criteria

## 4.1 Primary product goals

**Goal 1 — Personalized selection**

Generate a curated gallery that reflects the photographer's demonstrated preferences rather than generic visual quality alone.

**Goal 2 — Efficient learning**

Gather useful preference signals through approximately 20–40 pairwise comparisons.

**Goal 3 — Creative direction alignment**

Interpret a free-text creative brief and apply it when evaluating the gallery.

**Goal 4 — Reduced gallery size**

Produce an initial proposed collection matching the photographer's requested target count.

**Goal 5 — Human control**

Allow photographers to review recommendations and remove unwanted photographs before finalizing.

**Goal 6 — Transparent uncertainty**

Identify recommendations that warrant additional human attention.

## 4.2 Initial research success criteria

The MVP will be evaluated primarily through photographer satisfaction.

Each participant will provide:

- One overall satisfaction rating.
- Optional qualitative comments.

The evaluation should also collect objective operational measurements:

- Number of photographs uploaded.
- Number of comparisons completed.
- Time spent in the comparison workflow.
- Total processing time.
- Number of proposed photographs removed.
- Number of photographs remaining at export.
- Number of recommendations flagged as uncertain.
- Model failures and incomplete processing attempts.

These measurements provide useful supporting evidence but do not replace the photographer's overall satisfaction assessment.

### Proposed evaluation question

"How satisfied are you with the final collection recommended by SelectIQ?"

**Rating scale:** 1–5

1 — Very dissatisfied  
2 — Dissatisfied  
3 — Neutral  
4 — Satisfied  
5 — Very satisfied

Optional follow-up:

"What did SelectIQ do well, and what would you change about the proposed selection?"

An initial research objective is to determine whether participants generally rate the proposed selections positively. A formal satisfaction threshold should be established before the pilot rather than chosen after reviewing the results.

## 4.3 Research hypotheses

The following are hypotheses to test, not guaranteed capabilities:

**H1:** Approximately 20–40 comparisons provide enough information to improve a project-specific preference model.

**H2:** Adaptive selection of comparisons provides more useful information than random comparison selection.

**H3:** Combining a creative brief with demonstrated preferences produces a collection that photographers find satisfying.

**H4:** Redundancy-aware selection improves the usefulness of the final gallery.

**H5:** The system can identify uncertain recommendations in a way that helps photographers review the results.

# 5. Target Users

## 5.1 Primary user

An independent photographer who regularly captures more photographs than they intend to keep.

For example:

- Wedding photographers.
- Event photographers.
- Portrait photographers.
- Documentary photographers.

The initial prototype will be tested with a small number of participating photographers who provide their own JPEG galleries.

## 5.2 User characteristics

The target user:

- Understands photographic composition and creative preferences.
- Has experience selecting photographs from larger galleries.
- Can describe a desired mood, aesthetic, or story.
- Can make relative comparisons between photographs.
- Wants assistance reducing repetitive selection work.
- Expects to maintain final control over the results.

# 6. MVP Scope

## 6.1 Included

The MVP must support:

1. Uploading a gallery of approximately 300 JPEG photographs.
2. Validating and processing uploaded photographs.
3. Entering a free-text creative brief.
4. Specifying a desired final collection size.
5. Analyzing technical and visual image characteristics.
6. Identifying visually similar photographs.
7. Generating adaptive image comparisons.
8. Capturing preferences between two photographs.
9. Capturing optional explanations for comparison choices.
10. Learning project-specific preferences.
11. Generating a proposed curated gallery.
12. Accounting for obvious photographic redundancy.
13. Flagging uncertain recommendations separately.
14. Reviewing the proposed gallery as an image grid.
15. Removing unwanted photographs.
16. Exporting a downloadable list of selected filenames.
17. Collecting an overall satisfaction rating and optional feedback.
18. Running the complete prototype locally on an Apple Silicon Mac.

## 6.2 Excluded

The MVP does not require:

- RAW image support.
- PNG or HEIC uploads.
- Video processing.
- Photo editing or color correction.
- Lightroom or Capture One integrations.
- Automatic album layout.
- Photo delivery to clients.
- Payment processing.
- Public user registration.
- Persistent photographer accounts.
- Cross-project preference learning.
- Cloud synchronization.
- Multi-user collaboration.
- Mobile-native applications.
- Large-scale hosted production infrastructure.
- Mandatory session recovery across visits.
- Automatic deletion of photographs from the user's original gallery.

The prototype must never modify or delete the photographer's original files.

# 7. End-to-End User Journey

## Step 1 — Upload a gallery

The photographer opens SelectIQ and selects a gallery containing approximately 300 JPEG photographs.

The application validates the files and prepares them for analysis.

The interface displays the number of accepted photographs and any errors.

**Expected result:** The gallery is ready for analysis.

## Step 2 — Describe the desired story

The photographer enters a free-text prompt explaining what the final gallery should convey.

Example:

"Create a warm, intimate story of this wedding. Prioritize candid expressions, emotional interactions, and meaningful moments. Avoid overly posed photographs."

The prompt is not constrained to predefined categories.

The application may display example prompts, but these are optional.

## Step 3 — Choose the target collection size

The photographer specifies the desired number of photographs.

Example:

- Uploaded photographs: 300
- Requested final collection: 80

The target may vary by project.

The system must reject invalid targets, including zero, negative values, and counts greater than the number of accepted photographs.

## Step 4 — Analyze the gallery

SelectIQ performs image processing to extract information relevant to selection.

This includes technical characteristics, visual representations, and relationships among photographs.

The user sees processing progress.

The exact internal models and processing architecture will be defined during technical planning.

## Step 5 — Begin adaptive comparisons

SelectIQ presents two photographs simultaneously.

The photographer chooses which photograph they prefer.

The system records the choice as evidence of relative preference.

It does not automatically eliminate the losing photograph.

The next comparison is selected according to the information the system needs to learn.

## Step 6 — Optionally explain preferences

After choosing a photograph, the photographer may provide a reason.

Suggested reasons include:

- Better composition.
- Stronger emotion.
- Better lighting.
- More natural expression.
- More relevant subject.
- Better match for the story.
- Better overall aesthetic.
- Other — custom explanation.

Explanations are optional.

The system should allow users to proceed quickly without entering text.

## Step 7 — Update the preference model

Each comparison contributes to the project's preference-learning process.

The system progressively adapts how it interprets the photographer's taste.

As learning progresses, SelectIQ should prioritize comparisons likely to improve its understanding or resolve uncertainty.

The learning process is unique to the current gallery.

## Step 8 — Complete the comparison phase

The expected comparison experience consists of approximately 20–40 decisions.

The system may identify continuing uncertainty.

However, it must not indefinitely require additional comparisons before generating a proposal.

After completing the comparison phase, SelectIQ proceeds with the available preference information.

## Step 9 — Generate the proposed collection

SelectIQ evaluates the gallery using:

- The creative brief.
- The photographer's choices.
- Optional comparison explanations.
- Technical image analysis.
- Visual similarity information.
- Learned project-specific preferences.
- The contribution each photograph makes to the proposed collection.

The application proposes exactly the requested number of photographs, subject to sufficient valid photographs being available.

For a requested target of 80, the initial selection must contain 80 unique photographs.

## Step 10 — Review the proposed gallery

The photographer sees the recommended photographs in a grid.

The application separately identifies uncertain selections that deserve additional review.

The photographer may inspect photographs and remove unwanted selections.

Removing a photograph decreases the final collection size.

There is no requirement to automatically replace it or retrain the preference model after removal.

## Step 11 — Export the selection

The photographer finalizes the collection and downloads a list of selected image filenames.

The original files remain unchanged.

## Step 12 — Evaluate SelectIQ

The photographer provides an overall satisfaction rating and optional comments.

This feedback supports evaluation of the research prototype.

# 8. Functional Requirements

## FR-01 — Gallery ingestion

**Priority: Must have**

The application shall:

- Accept JPEG/JPG files.
- Support galleries of approximately 300 photographs.
- Reject unsupported formats.
- Identify files that cannot be decoded.
- Preserve the association between a photograph and its original filename.
- Provide a clear upload status.

Each accepted photograph must have a unique internal identifier.

Duplicate filenames must not cause photographs to overwrite one another.

Exact duplicate files may be detected, but the system must not silently remove user-supplied photographs.

## FR-02 — Creative brief

**Priority: Must have**

The application shall provide a free-text field for describing the desired creative direction.

The brief may specify mood, style, subject matter, emotional tone, or storytelling priorities.

The system shall not require structured preference fields.

The creative brief shall remain available throughout the project.

## FR-03 — Target count

**Priority: Must have**

The photographer shall specify the desired final collection size.

The initial recommendation must match this target when enough valid photographs exist.

The target is not a mandatory count after manual review.

## FR-04 — Image analysis

**Priority: Must have**

The application shall analyze each valid photograph to extract image characteristics useful for ranking and comparison.

Required capabilities include:

- Basic technical-quality measurements.
- Visual feature representation.
- Similarity estimation between photographs.
- Detection of obvious visual redundancy.

The system must distinguish measured technical characteristics from subjective artistic quality.

No photograph may be excluded solely because it lost a pairwise comparison.

The implementation should avoid repeatedly processing the same image unnecessarily.

## FR-05 — Adaptive comparison generation

**Priority: Must have**

The system shall generate comparisons between two photographs.

The selection strategy must be adaptive rather than exclusively random.

Comparisons should include an appropriate mixture of:

- Similar photographs that reveal subtle preferences.
- Different photographs that reveal broader visual taste.
- Comparisons involving uncertain candidates.
- Comparisons that help distinguish plausible ranking outcomes.

The system should avoid wasting interactions on repeated, uninformative comparisons.

The objective is to maximize useful information from approximately 20–40 decisions.

## FR-06 — Comparison capture

**Priority: Must have**

For each comparison:

- Exactly two photographs shall be displayed.
- The photographer shall choose A or B.
- The selected photograph shall be recorded.
- The unselected photograph shall remain eligible for final inclusion.
- The application shall associate the choice with the correct project and photo IDs.
- The application shall advance to the next comparison after recording the choice.

The current required interaction is binary preference selection.

A tie or skip action is not required for the initial MVP.

## FR-07 — Optional reasons

**Priority: Must have**

The application shall allow an optional explanation after a comparison.

A reason refers to why the selected photograph is preferred to the other.

For example, selecting "Better emotion" means the chosen photograph conveys emotion more effectively in that comparison.

It does not automatically establish that emotion is the photographer's highest-priority criterion across the entire gallery.

The system may use these reasons to enrich preference learning, but it must operate correctly when no reasons are provided.

## FR-08 — Project-specific learning

**Priority: Must have**

SelectIQ shall learn from choices made during the current gallery session.

The learned preference representation shall apply only to that project.

Starting another gallery shall create a new learning context.

No cross-project personalization is required.

## FR-09 — Creative brief and preference conflicts

**Priority: Must have**

The creative brief provides initial guidance.

However, repeated demonstrated preferences may cause the system to adjust its interpretation of the desired style.

SelectIQ shall not interrupt the photographer solely because choices appear inconsistent with the original brief.

The system should preserve the original brief and the recorded choices for analysis and evaluation.

## FR-10 — Curated gallery generation

**Priority: Must have**

The system shall produce a proposed collection based on the user-selected target.

Selection should prioritize:

1. Alignment with demonstrated preferences.
2. Relevance to the intended creative direction.
3. Individual image quality and visual value.
4. Avoidance of obvious unnecessary repetition.
5. Additional visual variety when it meaningfully improves the collection.

These are conceptual priorities, not a fixed mathematical weighting formula.

There shall be no predetermined quotas for specific subjects, moods, or photographic moments.

Multiple similar photographs may be included when they contribute meaningful additional value.

The collection should primarily reflect the photographer's taste rather than artificially maximizing category diversity.

## FR-11 — Uncertainty identification

**Priority: Must have**

The system shall identify recommendations for which available evidence is insufficient to support a strong selection judgment.

Examples include:

- Weak preference-model evidence.
- Conflicting creative signals.
- Closely competing photographs.
- Unclear contribution to the overall gallery.
- Ambiguous selection among visually similar frames.

Uncertainty must not be represented as a guarantee of correctness or an arbitrary probability without calibration.

The product should distinguish uncertainty in a recommendation from low aesthetic quality.

## FR-12 — Uncertain-candidate review

**Priority: Must have**

Uncertain photographs included in the proposed collection shall appear in a separate review group.

For a requested 80-photo selection, the uncertain photographs are part of those 80, not additional recommendations.

For example:

- 65 regular recommendations.
- 15 uncertain recommendations.
- Total proposed collection: 80.

The review interface shall make it clear that uncertain photographs are still included in the proposal unless removed.

The photographer shall be able to inspect the reasons for uncertainty.

## FR-13 — Recommendation explanations

**Priority: Must have**

The application shall provide explanations for uncertain recommendations.

For other recommendations, explanations shall be available on demand.

Explanations should refer to relevant evidence such as creative-brief alignment, demonstrated preferences, or visual characteristics.

The system must not invent unsupported technical claims about photographs.

Explanations should be concise and understandable to photographers.

## FR-14 — Final review

**Priority: Must have**

The proposed collection shall be displayed in a photo grid.

The photographer shall be able to:

- View all recommended photographs.
- Inspect individual photographs at a larger size.
- Review uncertain recommendations.
- Remove individual photographs from the collection.
- See the updated number of selected photographs.
- Finalize the remaining collection.

The MVP does not require adding previously excluded photographs back into the collection.

## FR-15 — Manual removal

**Priority: Must have**

Removing a photograph shall:

- Remove it from the proposed final collection.
- Reduce the selection count by one.
- Leave all other selected photographs unchanged.
- Not automatically add a replacement.
- Not trigger mandatory model retraining.

For example, if SelectIQ proposes 80 photographs and the photographer removes eight, the final selection contains 72 photographs.

## FR-16 — Export

**Priority: Must have**

The system shall export a downloadable file containing the filenames of the final selected photographs.

A simple text file or CSV is acceptable.

Example:

```text
IMG_1023.jpg
IMG_1048.jpg
IMG_1102.jpg
IMG_1147.jpg
```

The export must reflect the photographer's final decisions, not the original unmodified AI proposal.

The output should preserve sufficient file identification to avoid ambiguity when names are duplicated.

The MVP does not require exporting copies of the photographs.

## FR-17 — Satisfaction evaluation

**Priority: Must have**

After reviewing the gallery, the photographer shall be able to submit:

- An overall 1–5 satisfaction rating.
- Optional written comments.

The application shall associate the evaluation with the corresponding project.

## FR-18 — Progress and error handling

**Priority: Must have**

The application shall provide meaningful status updates during:

- Gallery upload.
- Image analysis.
- Comparison processing.
- Final recommendation generation.

Errors must be displayed in understandable language.

The application must not display incomplete or invalid recommendation data as though it were a finished selection.

# 9. Adaptive Preference-Learning Requirements

Adaptive comparison is the central experimental capability of SelectIQ.

The system should progressively learn which visual characteristics influence the photographer's decisions.

## 9.1 Input signals

Preference learning may incorporate:

- Image feature representations.
- Pairwise preference outcomes.
- Optional reasons for those preferences.
- Creative-brief context.
- Information about uncertainty in the current preference model.

## 9.2 Initial comparisons

At the beginning of a session, the system has little direct evidence about the photographer's preferences.

Initial comparisons should provide coverage of different visual characteristics and relevant image groups.

The objective is to establish a useful starting preference representation.

## 9.3 Later comparisons

As preference evidence accumulates, the system should select comparisons that are likely to clarify its current uncertainty.

For example, if the photographer consistently favors candid interactions, the system might present photographs that differ in composition or emotional intensity to learn more nuanced preferences.

The system should not simply repeat variations of the same already-established choice.

## 9.4 Learning behavior

After a choice is recorded, the system should be capable of incorporating that signal into subsequent ranking and comparison selection.

The exact timing of model updates may depend on technical feasibility.

The product requirement is that later comparisons meaningfully reflect information learned earlier in the session.

## 9.5 Comparison limit

The target interaction budget is 20–40 comparisons.

The system shall produce a proposed collection after the configured comparison phase even when unresolved uncertainty remains.

Low confidence must be communicated through the final review rather than hidden.

## 9.6 Feedback semantics

Choosing A over B means:

"Given these two photographs in this project, I prefer A."

It does not mean:

- B is a bad photograph.
- B should automatically be rejected.
- A must be included in the final gallery.
- The chosen reason is universally more important than all other criteria.

# 10. Gallery Curation Requirements

The final selection should be evaluated as a collection, not just as independent image scores.

## 10.1 Personal preference

Learned photographer preferences should play a major role in determining which photographs are selected.

## 10.2 Creative direction

The initial prompt should guide how the system interprets the project's intended mood, aesthetic, and story.

## 10.3 Redundancy

The system should recognize cases where several photographs provide essentially the same visual information.

However, it must not enforce an automatic one-photo-per-group rule.

Related photographs can coexist if they have meaningful differences.

## 10.4 Diversity

Diversity is a secondary consideration.

It should help prevent obvious repetitive selections but should not override strong preference evidence merely to achieve category balance.

## 10.5 Selection eligibility

All valid photographs remain eligible for the proposed collection throughout the learning phase.

Technical analysis and comparison outcomes may influence rankings but must not silently remove candidates from consideration.

## 10.6 Final collection size

The system must propose the requested number of unique photographs when sufficient valid images exist.

After manual review, the final count may be lower.

# 11. Confidence and Validation

SelectIQ needs two different kinds of confidence handling.

## 11.1 Recommendation uncertainty

The system must identify photographs where its selection judgment is uncertain.

Uncertainty should be informed by available model evidence and not fabricated.

The initial prototype may use heuristic uncertainty indicators, but these should be clearly distinguished from statistically calibrated probabilities.

## 11.2 Output validity

Before displaying the proposed collection, the application must verify:

- Every recommended photograph belongs to the uploaded project.
- Every recommended ID is unique.
- The initial selection count matches the requested target.
- Recommendation categories and identifiers are valid.
- Uncertain recommendations are accurately associated with the review group.
- Every displayed explanation is associated with the correct photograph.
- No unsupported technical measurements are presented as facts.
- The final export reflects the reviewed selection.

If recommendation generation fails, the application must report the problem or provide a clearly identified fallback.

It must not silently present an incomplete gallery as a validated recommendation.

# 12. UX Requirements

## 12.1 Design priorities

The user interface should prioritize:

- Visual clarity.
- Large photographic previews.
- Minimal unnecessary text.
- Fast comparison interaction.
- Clear progress information.
- Easy final review.

## 12.2 Required screens

**Screen 1 — Gallery Upload**

Displays upload control, accepted-photo count, and validation errors.

**Screen 2 — Creative Brief**

Allows a free-text prompt and target count.

**Screen 3 — Processing**

Shows image-analysis progress and status.

**Screen 4 — Pairwise Comparison**

Displays photograph A and photograph B side by side with selection controls and optional reasons.

**Screen 5 — Proposed Gallery**

Displays the curated collection in a grid and identifies the total proposed count.

**Screen 6 — Uncertain Recommendations**

Displays uncertain photographs separately with explanations and removal controls.

**Screen 7 — Finalize and Export**

Shows the remaining count and provides the filename-list download.

**Screen 8 — Evaluation**

Collects the satisfaction rating and optional comments.

The proposed gallery and uncertain recommendations may be implemented as separate views within the same screen.

# 13. Nonfunctional Requirements

## 13.1 Performance

The application must support approximately 300 JPEG photographs per project.

Image processing should avoid unnecessary repeated computation.

Quality has priority over processing speed.

Processing times of 10 minutes or longer are acceptable during the research prototype, provided that users receive clear progress feedback and the process eventually completes or reports a failure.

No strict processing-time service-level agreement is required.

## 13.2 Hardware compatibility

The prototype must run on an Apple Silicon Mac.

Specific hardware acceleration and model-execution decisions will be determined during technical feasibility testing.

The application should not assume that a dedicated NVIDIA GPU is available.

## 13.3 Budget

The initial demonstration should ideally use free components and require no more than approximately $25 in external services.

This is a target budget, not yet a verified feasibility guarantee.

Recurring cloud hosting and commercial-scale usage are outside MVP scope.

## 13.4 Reliability

The application must handle malformed images, unsuccessful processing jobs, and model failures without silently corrupting the project state.

Temporary state should be preserved during an active session sufficiently to support the end-to-end workflow.

Persistent sessions across days or devices are not required.

## 13.5 Privacy

Photographs are supplied by participating photographers and may contain private individuals or client material.

The research prototype must:

- Use photographs only with appropriate participant permission.
- Avoid modifying original files.
- Limit unnecessary exposure of image content.
- Clearly disclose any third-party image-processing services.
- Avoid indefinite retention of uploaded images.
- Support deletion of temporary project data after evaluation.

The detailed retention period and any model-provider processing agreements must be determined before testing with participant galleries.

## 13.6 Explainability

Explanations should help photographers understand recommendations without implying that subjective artistic judgment can be objectively proven.

## 13.7 Observability

The prototype should record enough information to investigate:

- Failed image-processing steps.
- Comparison-generation behavior.
- Model uncertainty.
- Final selection validity.
- Processing duration.
- Resource usage.
- Evaluation results.

# 14. Research Evaluation Plan

## 14.1 Study participants

Recruit a small group of photographers willing to provide galleries and evaluate the results.

The exact participant count depends on availability.

## 14.2 Study procedure

For each participant:

1. Obtain a permitted JPEG gallery.
2. Record the uploaded image count.
3. Ask the photographer to enter a creative brief.
4. Ask them to choose a target collection size.
5. Run the SelectIQ comparison workflow.
6. Generate the proposed collection.
7. Present uncertain recommendations separately.
8. Allow removal of unwanted photographs.
9. Export the final selection.
10. Collect the satisfaction rating and comments.

## 14.3 Primary outcome

Overall photographer satisfaction with the proposed curated gallery.

## 14.4 Secondary outcomes

- Number of comparisons required.
- Fraction of proposed images removed.
- Number of uncertain recommendations.
- Time to produce the proposal.
- Photographer comments about relevance and missing content.
- System failures or usability problems.

## 14.5 Evaluation limitations

A subjective satisfaction rating cannot prove that the model selected an objectively optimal gallery.

The initial study will establish whether photographers find the recommendations useful and aligned with their preferences.

Claims about objectively superior rankings, large reductions in total culling time, or generalization to all photographers would require additional controlled evaluation.

# 15. Acceptance Criteria

The MVP will be considered functionally complete when the following end-to-end demonstration succeeds.

### AC-01 — Upload

A participant can upload a gallery of 300 valid JPEG photographs.

The system accounts for all accepted photographs and reports failures clearly.

### AC-02 — Creative brief

The participant can submit a free-text description of the desired story.

The system associates the brief with the current project.

### AC-03 — Target count

The participant can request an 80-photo collection.

The requested target is stored correctly.

### AC-04 — Image analysis

All valid photographs are processed into representations that can support comparison and ranking.

### AC-05 — Adaptive comparisons

The participant completes approximately 20–40 A/B comparisons.

Later comparison choices are informed by earlier feedback, rather than following a fixed random sequence.

### AC-06 — Optional feedback

The participant can supply a predefined reason or custom explanation for a choice.

Skipping the explanation does not block progress.

### AC-07 — No automatic elimination

A photograph that loses a pairwise comparison remains eligible for the final selection.

### AC-08 — Proposed collection

The system generates 80 unique recommendations from the 300-photo gallery.

Every recommended photograph corresponds to an uploaded image.

### AC-09 — Uncertainty

Uncertain recommended photographs are displayed separately, but are counted within the 80-photo proposal.

Relevant explanations are available.

### AC-10 — Review

The participant can view the complete proposed collection and remove unwanted photographs.

### AC-11 — Removal behavior

Removing five photographs from the 80-photo proposal results in 75 selected photographs.

No replacements are automatically inserted.

### AC-12 — Export

The participant can download a filename list identifying those 75 remaining photographs.

### AC-13 — Evaluation

The participant can submit a satisfaction rating and optional comments.

### AC-14 — Local operation

The complete demonstration can run on the designated Apple Silicon Mac without requiring a production cloud deployment.

### AC-15 — Budget

External service spending for the initial demonstration remains within the agreed budget, or any necessary exception is explicitly identified before implementation.

# 16. Assumptions

The PRD relies on the following assumptions:

1. Test galleries will primarily contain approximately 300 JPEG photographs.
2. Participating photographers have permission to supply their photographs for testing.
3. A photographer can communicate a useful creative objective through free text.
4. Pairwise preferences contain information relevant to final gallery selection.
5. A limited comparison budget may provide useful personalization.
6. The available Apple Silicon Mac can perform the required processing, possibly with some external model assistance.
7. The prototype will be evaluated primarily through subjective participant satisfaction.
8. A single-session workflow is acceptable for the research demonstration.
9. The final export does not need to contain image files.
10. The photographer is responsible for final creative decisions.

These assumptions should be revisited if testing shows they are invalid.

# 17. Technical Feasibility Risks

These are not reasons to change the confirmed product requirements. They are questions the implementation must answer experimentally.

## Risk 1 — Insufficient preference information

Twenty to forty comparisons may not fully reveal the photographer's preferences across 300 images.

**Mitigation:** Evaluate learning quality at different comparison counts and communicate uncertainty.

## Risk 2 — Preference overfitting

The model may learn superficial characteristics of the presented pairs rather than broadly useful creative preferences.

**Mitigation:** Use diverse training comparisons and evaluate recommendations on photographs not directly compared.

## Risk 3 — Weak storytelling coherence

Ranking images individually may not produce a compelling collection.

**Mitigation:** Include collection-level redundancy and coherence considerations during selection.

## Risk 4 — Unreliable image similarity

Images depicting the same moment may be difficult to distinguish from unrelated photographs of similar subjects.

**Mitigation:** Evaluate grouping quality using real galleries and avoid using similarity alone to reject photographs.

## Risk 5 — Conflicting signals

A creative brief and pairwise comparisons may imply different preferences.

**Mitigation:** Define an adaptive interpretation strategy that prioritizes demonstrated preferences without discarding the original brief.

## Risk 6 — Poor uncertainty estimates

Model confidence may not correlate with actual recommendation quality.

**Mitigation:** Evaluate uncertainty indicators and avoid claiming statistical confidence without calibration.

## Risk 7 — Limited local computing resources

Running image models on Apple Silicon may consume significant processing time or memory.

**Mitigation:** Benchmark selected models and adjust the implementation without compromising core product behavior.

## Risk 8 — Restricted budget

Certain image-processing or multimodal reasoning approaches may exceed the $25 demonstration budget.

**Mitigation:** Evaluate local and low-cost approaches before committing to external inference services.

## Risk 9 — Evaluation bias

Participants may rate a visually appealing gallery positively even when the AI omitted photographs they would normally consider essential.

**Mitigation:** Preserve optional qualitative comments and track removal behavior. More rigorous accuracy evaluation can be added after the MVP.

## Risk 10 — Privacy and permissions

Participant-supplied galleries may contain identifiable people or private events.

**Mitigation:** Use permissioned galleries, disclose processing methods, and establish data-retention controls before testing.

# 18. Project Milestones

These are delivery milestones rather than fixed calendar commitments.

**Milestone 1 — Product specification complete**

Approve the PRD and acceptance criteria.

**Milestone 2 — Image-processing feasibility**

Demonstrate successful analysis of a 300-image JPEG gallery on the target hardware.

**Milestone 3 — Preference-learning feasibility**

Demonstrate that user comparisons can update a project-specific preference representation and influence later comparisons.

**Milestone 4 — Gallery recommendation prototype**

Generate a curated collection of a user-specified size while considering preferences, creative direction, and redundancy.

**Milestone 5 — Complete user workflow**

Implement upload, prompt entry, comparison, review, removal, export, and satisfaction feedback.

**Milestone 6 — Research evaluation**

Conduct tests with photographer-supplied galleries and analyze satisfaction, usability, processing behavior, and limitations.

# 19. Future Enhancements — Outside MVP

Potential future functionality includes:

- Persistent user accounts.
- Preference profiles that improve across projects.
- RAW image support.
- Larger galleries.
- Full-resolution export.
- Lightroom integration.
- AI-suggested replacement photographs.
- Additional comparison rounds initiated during final review.
- Group comparisons involving more than two photographs.
- Fine-grained storytelling controls.
- Fully hosted deployment.
- Multi-device access.
- Confidence calibration using larger evaluation datasets.
- Comparisons against manually curated ground-truth galleries.

These should not delay delivery of the research prototype.

# 20. Definition of Done

SelectIQ v1 is complete when a photographer can perform the following workflow successfully:

**Upload 300 JPEG images → describe the desired story → choose a target of 80 images → make approximately 20–40 adaptive A/B choices → receive a personalized 80-image proposal → review uncertain recommendations → remove unwanted images → export the final filename list → rate satisfaction.**

The prototype must demonstrate that these steps form a functioning, integrated system on an Apple Silicon Mac within the intended research budget.

Functional completion does not automatically establish that the AI is accurate or that the product meaningfully improves professional culling.

Those claims depend on the results of the photographer evaluation.

---

# 21. Product Summary

SelectIQ is an interactive AI photo culling research prototype that combines a creative brief with project-specific photographer preferences to produce a curated collection from a larger gallery.

Its defining characteristics are:

- **Personalized:** Learns from the photographer's choices during the project.
- **Adaptive:** Selects comparisons based on what remains uncertain.
- **Creative:** Uses the intended story rather than technical quality alone.
- **Collection-aware:** Avoids unnecessary repetition while preserving valuable related photographs.
- **Transparent:** Highlights uncertain recommendations.
- **Human-controlled:** Allows the photographer to remove suggestions before finalizing.
- **Focused:** Demonstrates a single meaningful capability without unnecessary commercial platform features.

**The core research question is whether a relatively small number of intelligently selected human comparisons can guide AI toward a photographic collection that genuinely reflects an individual creator's intent.**

That question drives the MVP's requirements, implementation priorities, and evaluation.
