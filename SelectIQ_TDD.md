# SelectIQ — Technical Design Document (TDD)

**Version:** 1.1<br>
**Status:** Proposed technical architecture, pending implementation benchmarks  
**Product requirements:** SelectIQ PRD v1.2<br>
**Target deployment:** Local Apple Silicon Mac  
**Input:** Approximately 300 JPEG photographs and one creative brief  
**Output:** User-selected number of curated photographs, uncertainty indicators, and downloadable filename list  
**Primary interaction:** Approximately 20–40 adaptive A/B comparisons  
**Cost objective:** Free or under $25 in external services for the initial demonstration

---

# 1. Executive Technical Summary

SelectIQ will be implemented as a local web application with a Python-based image-processing and machine-learning engine.

The application will ingest approximately 300 JPEG photographs, generate visual representations of each photograph, interpret a free-text creative brief, and learn the photographer's preferences through a short sequence of adaptively selected image comparisons.

Once the comparison phase is complete, SelectIQ will score eligible photographs and construct a proposed collection matching the photographer's requested target.

The system will prioritize personal preferences and creative-brief alignment while limiting unnecessary repetition.

A separate uncertainty analysis will identify photographs requiring closer human review.

The photographer can remove any proposed photograph and download the remaining filenames.

## 1.1 Principal architectural decision

The system will use a hybrid approach combining:

1. Deterministic image processing.
2. Pretrained image/text embeddings.
3. Lightweight preference learning.
4. Active comparison selection.
5. Collection-level optimization.
6. Targeted multimodal reasoning.
7. Deterministic output validation.

This architecture avoids the need to train a foundation model or rely on a single LLM to make every selection decision.

## 1.2 What we will actually build

We will implement the product-specific intelligence ourselves:

- Photograph ingestion and analysis pipeline.
- Near-duplicate and related-moment grouping.
- Adaptive comparison selection algorithm.
- Project-specific preference-learning model.
- Selection scoring and collection optimizer.
- Uncertainty estimation.
- Validation and export.
- Photographer-facing review interface.

We will reuse pretrained visual models and established numerical and web-development libraries.

## 1.3 Research-first implementation

The first major milestone will not be the complete frontend.

It will be a command-line prototype that can:

1. Load 300 JPEG images.
2. Generate feature representations.
3. Compare images numerically.
4. Accept simulated or manually entered A/B preferences.
5. Update a ranking model.
6. Produce a proposed 80-photo selection.
7. Explain which images have uncertain ranking positions.

This proves the core architecture before the graphical workflow is developed.

---

# 2. Development Environment

## 2.1 Hardware

The prototype is intended for an Apple Silicon Mac.

Supported development target:

- M1, M2, M3, M4, or newer Apple Silicon processor.
- macOS compatible with the selected Python and ML library versions.
- No NVIDIA GPU requirement.
- Local filesystem access.
- Browser-based frontend.

### Memory considerations

The exact RAM requirement depends on the pretrained models selected.

Development guidance:

| Mac configuration | Proposed operating approach |
|---|---|
| 8 GB unified memory | Small vision model, limited inference batches, avoid a large local multimodal model |
| 16 GB unified memory | Preferred baseline for local embeddings and lightweight ML |
| 24–32 GB or more | Greater flexibility for local multimodal inference |

These are planning guidelines, not verified minimum specifications.

The actual machine must be benchmarked before finalizing model size, concurrency, and memory limits.

## 2.2 Software

Recommended development tools:

- VS Code.
- Python 3.11 or a compatible verified release.
- Node.js LTS.
- Git and GitHub.
- Python virtual environment or uv for dependency management.
- npm for frontend dependencies.
- macOS Terminal.
- PyTorch with MPS support.

The Python and Node.js versions should be pinned after confirming compatibility.

## 2.3 Local execution

The MVP should have three logical processes:

**Frontend:** Runs the browser-based interface.

**API:** Handles requests, project state, and results.

**Processing worker:** Performs image analysis, ML inference, and curation.

The worker should execute natively on macOS rather than being forced into a container that might restrict Metal/MPS access.

All three components run on the same computer for the MVP.

## 2.4 Startup behavior

A typical development session will involve:

1. Start the local API.
2. Start the processing worker.
3. Start the frontend development server.
4. Open SelectIQ in a browser.
5. Upload a test gallery.
6. Complete the full workflow.

Eventually, these steps can be wrapped in a single developer startup script.

---

# 3. Recommended Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | React + TypeScript + Vite | Lightweight local browser application |
| Styling | Tailwind CSS | Rapid, consistent interface development |
| Backend | Python + FastAPI | Strong integration with ML tooling |
| Data validation | Pydantic | Typed API contracts and output validation |
| Session database | SQLite | Simple local persistence without a database server |
| File storage | Local filesystem | Avoid cloud storage cost |
| Image decoding | Pillow | JPEG loading, orientation, resizing |
| Image metrics | OpenCV + NumPy | Exposure, sharpness, contrast |
| Visual encoder | OpenCLIP | Pretrained image and text embeddings |
| ML inference | PyTorch | Local model execution |
| Preference learning | NumPy + scikit-learn | Regularized pairwise ranking |
| Pair selection | Custom Python implementation | Active-learning logic specific to SelectIQ |
| Collection optimization | Custom Python implementation | Target count, preference, redundancy |
| Multimodal reasoning | Configurable local or hosted model adapter | Contextual judgments and explanations |
| Testing | pytest + Playwright | Algorithm and end-to-end UI testing |
| Dependency management | uv or pip | Reproducible Python environment |

### Why React + Vite instead of Next.js?

For a local research prototype, we do not need server-side rendering, public SEO, or the deployment features of a full-stack React framework.

Vite provides a simpler development environment for the required upload, comparison, and gallery screens.

### Why SQLite instead of PostgreSQL?

Only a few galleries will be tested, and the application runs on one machine.

SQLite can store all the necessary project metadata, comparisons, scores, and selections.

The image files and embeddings remain on disk.

### Why not Redis or a distributed job queue?

We expect one active research session at a time.

A dedicated Python worker and a lightweight local job mechanism are sufficient.

This design can later be upgraded to a distributed queue if SelectIQ becomes a hosted product.

---

# 4. System Architecture

## 4.1 Main modules

The backend will be divided into nine modules.

**Module A — Project Management**

Creates projects and manages their lifecycle.

**Module B — Image Ingestion**

Validates JPEGs and prepares image representations.

**Module C — Visual Feature Extraction**

Generates technical metrics and image embeddings.

**Module D — Similarity Analysis**

Identifies duplicates and related photographs.

**Module E — Creative Brief Interpretation**

Translates free-text creative direction into usable model signals.

**Module F — Adaptive Comparison Engine**

Chooses the next A/B pair.

**Module G — Preference Model**

Learns the photographer's ranking preferences.

**Module H — Gallery Curation Engine**

Builds a user-targeted collection with redundancy control.

**Module I — Validation and Export**

Checks selection consistency and generates the final filename list.

## 4.2 Complete data flow

1. The user uploads image files through the browser.
2. The API stores them in a temporary project folder.
3. The image processor validates and normalizes each photograph.
4. Technical measurements are calculated.
5. Image embeddings are generated in batches.
6. Pairwise similarity and related-image groups are computed.
7. The creative brief is converted into semantic guidance.
8. The comparison engine selects the initial A/B pair.
9. The photographer selects a preferred photograph.
10. The preference model updates.
11. The comparison engine selects the next informative pair.
12. Steps 9–11 repeat until the comparison budget is reached.
13. The curation engine evaluates all eligible photographs.
14. The system constructs a proposed collection.
15. Uncertainty indicators are generated.
16. The validator verifies the complete proposal.
17. The user reviews and removes photographs.
18. The final filename list is exported.
19. Satisfaction feedback is stored.

---

# 5. Image Ingestion and Preprocessing

## 5.1 Objective

Convert the uploaded JPEG gallery into consistent image representations without repeatedly decoding full-resolution photographs.

## 5.2 Input validation

For each file:

1. Verify that the file can be decoded as JPEG.
2. Enforce an upload-size ceiling.
3. Enforce a maximum decoded pixel count.
4. Extract width, height, and permitted metadata.
5. Assign a unique internal photo ID.
6. Preserve the original filename.
7. Compute a content hash.
8. Record any processing errors.

File extensions alone are insufficient to verify format.

Invalid images must not crash processing for the entire gallery.

## 5.3 Image representations

Each accepted photograph will have three representations.

**Original uploaded copy**

The temporary JPEG supplied by the photographer.

**Analysis image**

A resized representation suitable for most technical measurements and detailed visual analysis.

Proposed initial maximum: 1600 pixels on the longest side.

**Thumbnail**

A smaller representation for the browser.

Proposed initial maximum: 400 pixels on the longest side.

The visual model will apply its own required input preprocessing.

## 5.4 Orientation and color

The preprocessing stage will:

- Apply EXIF orientation.
- Convert image content to a consistent RGB representation.
- Avoid modifying the original uploaded file.
- Normalize image handling without applying artistic edits.

## 5.5 Memory efficiency

Images should be processed incrementally.

The worker must avoid loading 300 full-resolution decoded images simultaneously.

A photograph is decoded, analyzed, and released before unnecessary memory accumulation occurs.

The worker may process small batches in parallel, subject to hardware benchmarks.

## 5.6 Error handling

Each photograph receives one of the following processing states:

- Pending.
- Processing.
- Completed.
- Failed.

A failure should include an error code and human-readable description.

If some photographs are invalid, the application should clearly identify the accepted gallery size before the preference-learning phase begins.

---

# 6. Technical Image Analysis

## 6.1 Objective

Collect inexpensive, interpretable signals about technical image characteristics.

Technical quality is one feature of photographic value, not the final selection criterion.

## 6.2 Proposed measurements

### Sharpness

Compute an estimate of image detail using a Laplacian-based sharpness metric.

The metric can help flag possible blur.

However, low sharpness does not always imply that a photograph is undesirable.

### Exposure

Measure brightness distribution and potential highlight or shadow clipping.

Relevant outputs include:

- Mean luminance.
- Fraction of very dark pixels.
- Fraction of very bright pixels.

### Contrast

Calculate contrast-related statistics from luminance.

### Image metadata

Record:

- Image dimensions.
- Aspect ratio.
- File size.
- Capture time, when available.
- Relevant technical metadata.

## 6.3 Important restriction

The system must not automatically reject a photograph because one technical metric falls below a fixed threshold.

Technical thresholds should be calibrated against actual photographic examples.

## 6.4 Output

Example internal record:

```json
{
  "photo_id": "p_0042",
  "sharpness_score": 116.7,
  "mean_luminance": 0.52,
  "dark_pixel_fraction": 0.04,
  "bright_pixel_fraction": 0.02,
  "contrast_score": 0.19,
  "width": 6000,
  "height": 4000
}
```

These example numbers are illustrative, not calibrated quality thresholds.

---

# 7. Visual Embeddings

## 7.1 Objective

Represent every photograph numerically so that the system can compare visual content and learn preferences.

## 7.2 Selected approach

Use a pretrained vision-language encoder.

The recommended initial candidate is OpenCLIP ViT-B/32.

This model produces compact embeddings suitable for similarity calculations and preference modeling.

It supports both image and text representations within a shared embedding space.

## 7.3 Inference procedure

For each image:

1. Load the normalized image.
2. Apply the encoder's required preprocessing.
3. Run the pretrained encoder.
4. Obtain its image embedding.
5. Normalize the vector.
6. Save the embedding with the photo ID.

The model is loaded once per worker process.

Inference is performed in batches.

## 7.4 Apple Silicon execution

Use PyTorch's MPS backend when compatible.

If MPS is unavailable or a required operation is unsupported, the processing module should support a CPU fallback.

Initial batch sizes should be benchmarked rather than assumed.

Suggested trials:

- 4 images.
- 8 images.
- 16 images.
- 32 images when memory permits.

## 7.5 Storage format

The full embedding matrix can be stored as a NumPy artifact.

For 300 images and 512 float32 values per image, raw embedding data requires approximately 0.6 MB.

No external vector database is required.

## 7.6 Model versioning

Store:

- Encoder name.
- Pretrained checkpoint identifier.
- Preprocessing version.
- Embedding dimension.
- Embedding artifact location.

This prevents mixing embeddings from incompatible encoders.

---

# 8. Photograph Similarity and Grouping

## 8.1 Objective

Identify photographs that are visually identical, nearly identical, or related to the same photographic moment.

Grouping supports both adaptive comparisons and final redundancy control.

## 8.2 Three similarity levels

### Level 1 — Exact duplicates

Use content hashes to detect byte-identical files.

Do not silently delete duplicates from the project.

### Level 2 — Near-duplicates

Use perceptual similarity measurements to identify photographs with nearly identical visual content.

Possible signals:

- Perceptual hash distance.
- Image embedding similarity.
- Capture-time proximity.

### Level 3 — Related moments

Use semantic embedding similarity and available metadata to identify photographs that depict related subjects or events.

For example, photographs of the same wedding dance may belong to one broad related-moment group while containing several visually distinct frames.

## 8.3 Similarity calculations

For normalized embeddings, cosine similarity can be computed through matrix multiplication.

For 300 images, this creates a 300 × 300 similarity matrix.

The computation is small enough to perform locally.

## 8.4 Grouping strategy

The first implementation should use threshold-based grouping and connected components or a comparable simple clustering approach.

Similarity thresholds must be evaluated on real galleries.

A high semantic similarity score does not automatically mean that photographs are interchangeable.

## 8.5 Group-level information

Each group should store:

- Group identifier.
- Member photographs.
- Similarity statistics.
- Representative photograph.
- Optional capture-time range.
- Grouping confidence or quality indicators.

## 8.6 Grouping restrictions

No group may enforce a one-photo-only selection rule.

Multiple group members may appear in the final collection.

Grouping is evidence about redundancy, not proof that only one image has value.

---

# 9. Creative Brief Interpretation

## 9.1 Objective

Convert the photographer's free-text creative direction into signals that can guide the initial ranking and later curation.

## 9.2 Example brief

"Show the warmth and excitement of the wedding, focusing on genuine family interactions, spontaneous laughter, and intimate moments rather than formal posed portraits."

## 9.3 Proposed interpretation

The system should extract or represent:

- Positive creative priorities.
- Negative or deprioritized characteristics.
- Desired emotional tone.
- Desired subjects or interactions.
- Aesthetic preferences.
- Storytelling intent.

## 9.4 Initial implementation

Use the text capabilities of the pretrained vision-language encoder to compare brief-related descriptions with image embeddings.

Because CLIP-style text encoders have input-length limitations, unrestricted user prompts must not be passed blindly without checking tokenization and truncation.

The first implementation should:

1. Preserve the original prompt.
2. Create one or more short semantic descriptors.
3. Encode those descriptors using the text encoder.
4. Estimate alignment between each image and the descriptors.
5. Store relevance scores and descriptor provenance.

For straightforward briefs, simple descriptors may be sufficient.

More complex or abstract briefs may require multimodal reasoning.

## 9.5 Multimodal reasoning adapter

The system should expose a replaceable interface for a multimodal reasoning model.

Possible responsibilities:

- Interpret nuanced creative directions.
- Evaluate competing candidate photographs.
- Explain uncertain selection decisions.
- Distinguish semantic meaning that image embeddings alone fail to capture.

The MVP should avoid sending every high-resolution image through such a model.

Instead, multimodal analysis should prioritize selected candidate groups and ambiguous cases.

The exact local or hosted model will be selected after hardware and budget testing.

## 9.6 Conflicting preferences

The system shall not interrupt the photographer when the brief and their demonstrated choices conflict.

Repeated user choices may change the effective preference ranking.

The original brief remains recorded for evaluation.

---

# 10. Preference-Learning Model

This is one of the core custom algorithms in SelectIQ.

## 10.1 Objective

Learn a scoring function that estimates which photographs the photographer would prefer.

## 10.2 Training observations

A comparison produces:

- Photo A.
- Photo B.
- Selected winner.
- Optional explanation.
- Comparison sequence number.

Example:

```json
{
  "photo_a_id": "p_0031",
  "photo_b_id": "p_0104",
  "winner_id": "p_0031",
  "reason": "better_emotion",
  "sequence": 12
}
```

## 10.3 Initial mathematical approach

Use a regularized pairwise linear preference model.

Let:

- x_A represent the feature vector of photograph A.
- x_B represent the feature vector of photograph B.
- w represent learned preference weights.

Define:

score(A) = w · x_A

score(B) = w · x_B

The probability of preferring A is modeled as:

P(A preferred over B) = sigmoid(w · (x_A − x_B))

The model learns weights from pairwise choices.

## 10.4 Why lightweight learning?

Only 20–40 comparisons are available.

That amount of data is insufficient for reliable fine-tuning of a large visual encoder.

A regularized linear model provides a simpler experimental baseline.

The system should begin with pretrained representations and update only the project-specific preference parameters.

## 10.5 Feature design

Candidate features include:

- Compressed image embeddings.
- Technical measurements.
- Creative-brief relevance scores.
- Optional interpretable image properties.

The model should avoid using hundreds of unconstrained trainable coefficients without sufficient evidence.

Potential strategies include:

- Dimensionality reduction.
- Strong regularization.
- Smaller interpretable feature sets.
- Shrinkage toward a neutral prior.

The best feature representation must be benchmarked.

## 10.6 Training details

The implementation must avoid pair-order bias.

A choice of A over B should represent the same preference as B losing to A.

We should train on correctly signed feature differences and use label construction or augmentation that does not accidentally turn every recorded choice into the same target without preserving the orientation of the pair.

Regularization must prevent extreme weight estimates from a small number of comparisons.

## 10.7 Updating preferences

The model may be retrained after every comparison or after short batches of comparisons.

For a small dataset, retraining a lightweight model is inexpensive.

The recommended initial behavior is to update after each valid comparison.

## 10.8 Optional explanations

The first model should treat the A/B winner as the primary preference signal.

Optional reasons can be stored and used for interpretation.

However, we should not assume that selecting "better emotion" directly provides a reliable numerical emotion score.

A later implementation may use reason-specific image features or additional multimodal analysis.

## 10.9 Model output

For every photograph, produce:

- Learned preference score.
- Comparison-related uncertainty estimate.
- Model version.
- Number of comparisons used.

Preference scores are relative within the current project.

They should not be presented as universal photographic-quality ratings.

---

# 11. Adaptive Comparison Engine

## 11.1 Objective

Select useful A/B comparisons that improve the preference model within a limited interaction budget.

## 11.2 Why random comparisons are insufficient

Random comparisons can waste decisions on obvious or repetitive choices.

For example, repeatedly asking a photographer to choose between a strong candid portrait and an unrelated dark technical failure may reveal little new information after the photographer has demonstrated the same preference several times.

## 11.3 Proposed comparison strategy

Use a staged adaptive policy.

### Early stage — Exploration

Present comparisons that cover different visual characteristics.

Goals:

- Identify broad aesthetic preferences.
- Sample different parts of the gallery.
- Establish initial preference evidence.

### Middle stage — Learning refinement

Present pairs where model predictions remain uncertain.

Goals:

- Refine preference boundaries.
- Compare related photographs.
- Explore subtle differences in composition, emotion, or style.

### Late stage — Selection relevance

Prioritize comparisons whose outcomes could influence the proposed final gallery.

Goals:

- Distinguish candidates near the selection boundary.
- Resolve uncertainty between competing images.
- Improve the final collection rather than merely predict arbitrary pairwise choices.

## 11.4 Candidate-pair scoring

The comparison engine may rank candidate pairs using a weighted combination of:

- Preference-model uncertainty.
- Visual difference.
- Selection-boundary relevance.
- Previous exposure count.
- Similarity-group relationship.
- Expected informativeness.

The weights are experimental parameters.

They should be evaluated rather than treated as proven optimal values.

## 11.5 Exposure management

The system should prevent a small number of photographs from monopolizing comparisons.

Track how often each image has been displayed.

Previously asked pairs should not be repeated unless explicitly required for a controlled research experiment.

## 11.6 Comparison count

The intended interaction budget is approximately 20–40.

The initial implementation may use a default of 30 comparisons with a maximum of 40.

These are proposed engineering defaults, not changes to the PRD.

The model must generate a proposal at the end of the configured comparison phase.

## 11.7 Comparison result handling

After each choice:

1. Persist the comparison.
2. Update the preference model.
3. Refresh relevant ranking estimates.
4. Recalculate candidate-pair priorities.
5. Select the next comparison.
6. Return the comparison to the interface.

The next-pair computation should be sufficiently fast that it does not create noticeable interruption during the interaction loop.

---

# 12. Final Gallery Scoring

## 12.1 Objective

Combine available evidence into an initial value estimate for every photograph.

## 12.2 Proposed score components

The curation engine will consider:

- Project-specific preference score.
- Creative-brief relevance.
- Technical-quality evidence.
- Contextual multimodal assessments, where available.

A conceptual formula is:

value(i) =
  preference_component(i)
  + brief_component(i)
  + technical_component(i)
  + contextual_component(i)

This is not yet a finalized mathematical formula.

Each component must be normalized or calibrated before combining it with others.

Raw CLIP cosine similarity, unbounded model scores, and OpenCV sharpness values cannot be added directly and meaningfully without normalization.

## 12.3 Preference dominance

The photographer's demonstrated preferences should have substantial influence.

However, the system should account for weak evidence when the preference model has seen only a small number of comparisons.

One possible method is to increase reliance on learned preferences as supporting evidence accumulates.

This is a hypothesis to test.

## 12.4 Important distinction

The individual score estimates a photograph's value.

The collection optimizer determines whether including the photograph improves the selected collection.

These are different problems.

---

# 13. Collection-Level Optimization

## 13.1 Objective

Select exactly K photographs from N valid inputs.

Example:

N = 300  
K = 80

The system should maximize overall collection value while avoiding excessive redundancy.

## 13.2 Why top-K individual ranking is insufficient

Suppose the highest-ranked 20 images all show nearly identical frames of the same dance.

Selecting all 20 may produce unnecessary repetition.

A slightly lower-ranked image from another moment may improve the overall collection.

## 13.3 Proposed objective

Use a collection objective combining:

- Individual image value.
- Redundancy penalty.
- Optional coverage or diversity benefit.

Conceptually:

collection_value(S) =
  sum(individual_values)
  − redundancy_penalty(S)
  + modest_coverage_benefit(S)

Subject to:

- S contains exactly K unique photographs.
- Every selected photo belongs to the project.
- Multiple members of the same similarity group are permitted.

## 13.4 Initial optimization method

Use a deterministic greedy selection algorithm.

Procedure:

1. Begin with an empty selected collection.
2. Evaluate each remaining photograph's incremental contribution.
3. Choose the photograph with the greatest incremental value.
4. Update redundancy relationships.
5. Repeat until K photographs have been selected.

This provides a simple, explainable starting point.

## 13.5 Redundancy behavior

The redundancy penalty should increase when a candidate closely resembles photographs already selected.

However, the penalty must remain soft.

Related photographs can still be included if their individual values justify inclusion.

## 13.6 Stable selection

Given identical inputs, model versions, and random seeds, the curation algorithm should produce reproducible results.

The system should record the parameters and model versions used for each recommendation.

## 13.7 Target count

The initial generated proposal must contain exactly the requested target number when sufficient valid photographs are available.

The photographer's later removals are not replaced.

---

# 14. Uncertainty Estimation

## 14.1 Objective

Identify recommendations that deserve additional attention during final review.

## 14.2 Sources of uncertainty

Possible signals include:

- Limited preference evidence.
- Instability across plausible preference models.
- Small differences between alternative candidates.
- Weak alignment with the brief.
- Conflicting assessment signals.
- Ambiguous redundancy decisions.

## 14.3 Proposed method

Start with model-stability analysis.

For example:

1. Generate multiple alternative preference estimates from the available comparisons.
2. Recalculate photograph rankings.
3. Re-run collection selection.
4. Track how often each photograph appears in the proposed set.

Photographs whose inclusion is unstable can be flagged for additional review.

With only 20–40 observations, bootstrap-based estimates will themselves be noisy. They should be presented as heuristic stability indicators rather than calibrated correctness probabilities.

## 14.4 Review groups

The output contains:

- Regular recommendations.
- Uncertain recommendations.

Both groups are part of the requested collection.

Example:

Regular: 63  
Uncertain: 17  
Total: 80

## 14.5 Explanations

The system should generate specific reasons for uncertainty when supporting evidence exists.

Examples:

- "This photograph has similar predicted value to another frame from the same moment."
- "The model has limited evidence about this visual style."
- "Its selection changes across alternative preference estimates."

The application must not claim that a specific emotional interpretation has been verified if it has not.

---

# 15. Multimodal Reasoning Architecture

## 15.1 Role of multimodal AI

The multimodal model should complement rather than replace the numerical pipeline.

Its primary responsibilities are:

- Understanding complex creative requests.
- Evaluating nuanced candidate photographs.
- Comparing ambiguous visual content.
- Generating grounded explanations.
- Providing additional context for collection decisions.

## 15.2 Why not send every photo to an LLM?

Sending 300 high-resolution images to a model can be expensive and slow.

The model may also struggle to maintain consistent judgments across a large collection.

The proposed approach uses local image representations first and invokes multimodal reasoning selectively.

## 15.3 Model adapter

Implement an interface independent of the selected provider.

Example conceptual operations:

- interpret_brief()
- analyze_candidates()
- compare_candidate_group()
- explain_uncertainty()

The adapter will return structured data.

## 15.4 Candidate selection for multimodal reasoning

Prioritize:

- Photographs near the final selection boundary.
- Uncertain recommendations.
- Related groups with several competitive images.
- Cases where the brief requires interpretation beyond embedding similarity.

## 15.5 Cost control

The system should track:

- Number of model requests.
- Number of images supplied.
- Input and output usage where applicable.
- Estimated external cost.
- Request duration.

The prototype must enforce a configurable spending limit when hosted APIs are enabled.

## 15.6 Local feasibility

A local multimodal model may be possible on Apple Silicon, depending on available RAM and model compatibility.

This is not guaranteed.

The architecture must support a fallback that still produces a structurally valid collection using pretrained embeddings and preference learning, while clearly indicating if full multimodal creative reasoning was unavailable.

This fallback is a degraded mode, not equivalent evidence that the full generative-AI hypothesis has been demonstrated.

---

# 16. Data Storage and Models

## 16.1 Storage approach

SQLite will store project metadata and structured decisions.

Local directories will hold:

- Uploaded JPEG copies.
- Working images.
- Thumbnails.
- Embedding artifacts.
- Model artifacts.
- Logs.
- Export files.

## 16.2 Proposed relational entities

### Project

- project_id
- created_at
- creative_brief
- target_count
- status
- comparison_budget
- model_configuration

### Photo

- photo_id
- project_id
- original_filename
- original_path
- thumbnail_path
- content_hash
- width
- height
- processing_status

### PhotoFeature

- photo_id
- technical_metrics
- embedding_reference
- brief_relevance
- feature_version

### SimilarityGroup

- group_id
- project_id
- grouping_type
- grouping_version

### SimilarityGroupMember

- group_id
- photo_id

### Comparison

- comparison_id
- project_id
- photo_a_id
- photo_b_id
- winner_id
- optional_reason
- sequence_number

### PreferenceModel

- model_id
- project_id
- training_comparison_count
- model_artifact_path
- model_version

### Recommendation

- recommendation_id
- project_id
- photo_id
- proposal_version
- selected_status
- uncertainty_flag
- explanation
- relevant_scores

### Evaluation

- evaluation_id
- project_id
- satisfaction_rating
- optional_comments
- submitted_at

## 16.3 Referential integrity

Every photo ID must belong to the correct project.

A comparison cannot reference nonexistent photographs.

A recommendation cannot contain the same photo twice within one proposal.

## 16.4 Local lifecycle

Projects may be temporary.

The application should support removal of temporary project files after the demonstration.

Long-term accounts and project history are outside MVP scope.

---

# 17. API Design

The local frontend communicates with the Python API through HTTP.

Proposed endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /projects | Create project |
| POST | /projects/{id}/photos | Upload JPEGs |
| POST | /projects/{id}/analyze | Start processing |
| GET | /projects/{id}/status | Check progress |
| POST | /projects/{id}/brief | Save creative prompt and target |
| GET | /projects/{id}/comparison | Retrieve current A/B pair |
| POST | /projects/{id}/comparison | Submit a choice |
| POST | /projects/{id}/curate | Generate proposed collection |
| GET | /projects/{id}/recommendations | Retrieve proposal |
| DELETE | /projects/{id}/selection/{photoId} | Remove selected photo |
| GET | /projects/{id}/export | Download filenames |
| POST | /projects/{id}/evaluation | Save satisfaction feedback |

All endpoints must validate project ownership or session access.

For the initial single-user local prototype, a generated session token is sufficient, provided access to local project data is controlled.

---

# 18. Background Processing

## 18.1 Why background execution is necessary

Image decoding and ML inference can take substantially longer than normal HTTP requests.

The API must not block until all images have been processed.

## 18.2 Proposed worker design

Use a separate Python worker process that accepts queued job records.

The database tracks job state.

The initial MVP can use SQLite-backed job coordination or a similarly simple local mechanism.

## 18.3 Job lifecycle

- Queued.
- Running.
- Completed.
- Failed.
- Canceled.

## 18.4 Processing stages

A gallery-analysis job should include:

1. Input validation.
2. Image normalization.
3. Technical measurements.
4. Embedding inference.
5. Similarity grouping.
6. Brief-related scoring.
7. Completion and readiness notification.

## 18.5 Recovery

A failed image or interrupted process should not require repeating already completed work unnecessarily.

Processing stages should be idempotent where practical.

The worker should write intermediate artifacts atomically and update status only when results are complete.

---

# 19. Frontend Implementation

## 19.1 Application structure

The frontend will use React and TypeScript.

Primary pages or views:

- Upload.
- Creative brief and target.
- Processing progress.
- Adaptive comparisons.
- Proposed collection.
- Uncertain recommendations.
- Final export.
- Evaluation.

## 19.2 Pairwise comparison interface

Display two large photographic previews side by side.

Each image is selectable.

After selecting an image, allow optional quick reasons or custom text.

The interface should not require typing.

## 19.3 Comparison progress

Display current progress, such as:

"Comparison 18 of 30"

Do not display arbitrary confidence percentages as though they represent verified model certainty.

## 19.4 Review interface

Display:

- Proposed photo grid.
- Selected count.
- Uncertain recommendation group.
- Remove controls.
- Explanation-on-demand controls.
- Export action.

## 19.5 Performance

Thumbnails should be loaded efficiently and only as necessary.

Full-resolution files should not be sent to the browser merely to render a grid.

The interface should remain responsive during processing.

---

# 20. Validation and Failure Handling

## 20.1 Output schema validation

Every recommendation must contain valid identifiers and required fields.

## 20.2 Collection validation

Verify:

- All selected photographs are valid project members.
- No duplicate selected photo IDs exist.
- The initial target count is satisfied.
- Uncertain photographs are included in the target count.
- All scores and explanations correspond to the correct photographs.

## 20.3 Failure scenarios

### Corrupted JPEG

Skip the invalid image, record the error, and show the updated accepted count.

### Embedding model fails

Report processing failure and permit controlled retry.

### Preference model fails to train

Use a documented baseline preference strategy and clearly indicate that personalization is degraded.

### Multimodal API unavailable

Use the local numerical curation fallback, with degraded capability disclosed.

### Invalid recommendation output

Reject the invalid output and retry or reconstruct using deterministic selection rules.

### Browser refresh

Temporary project state should remain in the local backend during the active session, allowing practical recovery without requiring full cross-session account support.

### Export failure

Keep the selection intact and allow another export attempt.

---

# 21. Security and Privacy

The prototype processes photographs supplied by participating photographers.

Even though it runs locally, basic privacy controls remain necessary.

Requirements:

- Do not modify user originals.
- Store uploaded copies in project-specific directories.
- Prevent unrestricted file-path access through API parameters.
- Validate file types and sizes.
- Avoid executing metadata or arbitrary uploaded content.
- Restrict local API access appropriately.
- Do not expose private image files through unrestricted public URLs.
- Clearly disclose external model processing.
- Remove temporary data when no longer needed.
- Obtain appropriate permission before testing with participant galleries.

If any image content is transmitted to an external model provider, the participant must be informed before processing.

---

# 22. Testing Strategy

Testing must focus on algorithm correctness as well as visual output quality.

## 22.1 Unit tests

Test:

- JPEG validation.
- Resize and orientation handling.
- Technical feature calculations.
- Embedding normalization.
- Similarity calculations.
- Pairwise choice recording.
- Preference update behavior.
- Duplicate comparison prevention.
- Collection target constraints.
- Manual removal behavior.
- Filename export.

## 22.2 Synthetic ranking tests

Create synthetic feature vectors with known underlying preference weights.

Simulate user choices.

Verify that the preference model can recover useful ranking behavior.

This isolates bugs in the learning algorithm from limitations of visual embeddings.

## 22.3 Adaptive-learning tests

Compare adaptive pair selection with random pairs on controlled simulated users.

Measure ranking accuracy or agreement on held-out comparisons.

If adaptive selection does not outperform the baseline, reconsider the strategy before building additional complexity.

## 22.4 Real-gallery tests

Use permissioned galleries to evaluate:

- Grouping quality.
- Embedding relevance.
- Creative-brief alignment.
- Recommendation satisfaction.
- Perceived repetition.
- Uncertainty usefulness.

## 22.5 End-to-end test

Upload 300 JPEG photographs.

Enter a creative brief.

Request 80 photographs.

Complete 30 adaptive comparisons.

Generate an 80-photo proposal.

Remove five photographs.

Export 75 filenames.

Submit a satisfaction rating.

All stages must complete successfully.

---

# 23. Performance and Resource Testing

## 23.1 Required benchmark

Benchmark an actual 300-image gallery on the development Mac.

Measure:

- JPEG decoding time.
- Thumbnail generation time.
- Technical feature extraction time.
- Embedding generation time.
- Similarity grouping time.
- Preference update time.
- Next-pair generation time.
- Final collection optimization time.
- Multimodal inference time, where enabled.
- Peak memory usage.
- Total elapsed processing time.

## 23.2 Initial engineering targets

The following are proposed targets for evaluation rather than guaranteed capabilities:

- Support all 300 valid JPEGs without exhausting memory.
- Keep comparison submission and next-pair selection interactive.
- Compute similarity relationships without external infrastructure.
- Generate the final numerical proposal without sending every photograph to a hosted model.
- Keep external demonstration costs under $25.
- Provide correct output even when optional multimodal reasoning is unavailable.

## 23.3 Scaling strategy

For a 300-image local prototype:

- Use batched inference.
- Cache image embeddings.
- Keep embeddings in compact numerical arrays.
- Use efficient matrix operations.
- Avoid repeated full-resolution image decoding.
- Limit concurrent expensive ML tasks.
- Reuse completed feature artifacts.

This is sufficient without distributed compute.

---

# 24. Repository Structure

The Alpha uses a modular monorepo with one React frontend, one FastAPI backend, one reusable Python package, and one shared fixture/e2e test area. The detailed ownership rules and story mapping are defined in [ALPHA_REPO_STRUCTURE.md](ALPHA_REPO_STRUCTURE.md).

```text
Select_IQ/
├── frontend/                 # React workflow by user-facing feature
├── backend/
│   ├── src/selectiq/
│   │   ├── api/              # Thin FastAPI routes
│   │   ├── domain/           # Provider-independent product types
│   │   ├── application/      # Use-case orchestration
│   │   ├── intelligence/     # Brief, preference, curation, uncertainty
│   │   ├── infrastructure/   # SQLite, filesystem, model adapters
│   │   └── jobs/             # One local gallery-analysis runner
│   └── tests/                # Unit, integration, and contract tests
├── tests/
│   ├── e2e/                  # Complete Alpha photographer workflow
│   └── fixtures/
│       ├── sports/           # Sports manifests and expected behavior
│       └── retirement/       # Retirement manifests and expected behavior
├── scripts/                  # Dev, test, benchmark, and simulation tools
├── var/                      # Gitignored runtime projects/cache/exports/db
├── docs/                     # Evaluation notes and decisions
└── project specification documents
```

The `var/` directory must be excluded from Git.

Real photographer images and temporary model artifacts must not be committed unless they have explicit permission for public repository use. Fixture manifests may refer to private local galleries through environment configuration.

The Alpha remains a modular monolith. It does not require authentication packages, cloud storage, distributed queues, microservices, or Beta integrations.

---

# 25. Implementation Phases

## Phase 0 — Environment validation

**Goal:** Prove that the development machine can execute the required image encoder.

Tasks:

- Record hardware and macOS details.
- Install Python dependencies.
- Verify PyTorch inference on MPS.
- Verify CPU fallback.
- Load one pretrained image encoder.
- Process a small image batch.
- Record memory and processing time.

**Exit criterion:** A reproducible local embedding benchmark works.

## Phase 1 — Image pipeline

**Goal:** Process and represent a complete 300-image gallery.

Tasks:

- JPEG ingestion.
- Image validation.
- Orientation correction.
- Thumbnail generation.
- Technical metrics.
- Embeddings.
- Similarity grouping.

**Exit criterion:** All valid images have stored features and grouping metadata.

## Phase 2 — Preference learning

**Goal:** Learn from A/B comparisons.

Tasks:

- Define feature representation.
- Implement pairwise ranking.
- Store comparison outcomes.
- Update the ranking model.
- Evaluate on synthetic and held-out comparisons.

**Exit criterion:** The model responds consistently to new preference evidence.

## Phase 3 — Active comparison engine

**Goal:** Improve information gathering.

Tasks:

- Exploration policy.
- Uncertainty sampling.
- Boundary-focused sampling.
- Exposure balancing.
- Comparison deduplication.
- Random-baseline evaluation.

**Exit criterion:** Adaptive pair selection operates correctly and demonstrates measurable value on controlled tests.

## Phase 4 — Gallery curation

**Goal:** Produce a selected collection.

Tasks:

- Combine preference and brief scores.
- Implement redundancy-aware optimization.
- Enforce target counts.
- Add uncertainty indicators.
- Validate proposals.

**Exit criterion:** The system produces a valid 80-photo selection from 300 inputs.

## Phase 5 — Multimodal reasoning

**Goal:** Improve creative interpretation.

Tasks:

- Implement model adapter.
- Compare local and hosted model feasibility.
- Integrate targeted candidate analysis.
- Generate grounded explanations.
- Measure costs and effect on selection quality.

**Exit criterion:** Multimodal analysis is functional and its contribution is measured against the non-generative baseline.

## Phase 6 — User interface

**Goal:** Complete the photographer workflow.

Tasks:

- Upload page.
- Brief page.
- Comparison interface.
- Results grid.
- Uncertainty review.
- Removal controls.
- Export.
- Satisfaction rating.

**Exit criterion:** The complete user journey works locally.

## Phase 7 — Research evaluation

**Goal:** Evaluate whether the prototype fulfills its intended purpose.

Tasks:

- Run controlled photographer sessions.
- Collect satisfaction ratings.
- Record removals and uncertainty.
- Analyze qualitative feedback.
- Document limitations.
- Identify next engineering priorities.

**Exit criterion:** A completed evaluation report describes product usefulness and technical feasibility.

---

# 26. Key Engineering Risks and Decision Gates

## Gate A — Are visual embeddings good enough?

If pretrained image embeddings fail to distinguish meaningful photographic differences, evaluate stronger encoders or additional features.

Do not build the complete preference engine around an inadequate representation.

## Gate B — Can 20–40 comparisons teach useful preferences?

This is the primary research risk.

If the learned model performs no better than generic or random baselines, investigate feature choice, regularization, comparison selection, and whether preference learning should target a smaller set of interpretable characteristics.

## Gate C — Does adaptive sampling help?

An algorithm can be adaptive without actually being informative.

Measure its contribution rather than assuming it is superior to random sampling.

## Gate D — Does collection-level optimization improve the gallery?

Evaluate whether redundancy penalties improve satisfaction or simply exclude valuable photographs.

The optimizer must remain tunable.

## Gate E — Is multimodal reasoning necessary and affordable?

Measure the incremental value of multimodal reasoning against its runtime and external cost.

The application architecture supports the capability, but the selected model and frequency of use remain benchmark-dependent.

## Gate F — Is the application usable within one session?

Test the complete workflow on the intended development machine.

Long processing time is permissible, but the application must remain understandable and reliable.

---

# 27. Detailed Acceptance Test

The final system demonstration will use a real photographer-supplied gallery.

### Test configuration

- Input: 300 JPEG photographs.
- Creative brief: Supplied by the photographer.
- Target: 80 photographs.
- Comparison budget: 30 decisions, adjustable within the intended range.
- Runtime: Apple Silicon Mac.
- External service budget: Under $25.

### Test sequence

1. Launch SelectIQ locally.
2. Upload 300 JPEG images.
3. Validate the gallery.
4. Enter a creative brief.
5. Specify a target of 80.
6. Complete image analysis.
7. Receive the first A/B comparison.
8. Make 30 choices with optional explanations.
9. Observe adaptive selection of subsequent pairs.
10. Generate an 80-photo proposal.
11. Confirm all selected IDs are unique and valid.
12. Review uncertain recommendations.
13. Remove five selected photographs.
14. Verify that 75 photographs remain.
15. Download the filename list.
16. Verify that the export contains the 75 correct filenames.
17. Submit an overall satisfaction rating.

### Functional success

All workflow and validation requirements pass.

### Research success

The photographer reports satisfactory alignment with their intended gallery, and supporting logs allow the team to evaluate the quality and limitations of the preference-learning approach.

---

# 28. Final Architecture Recommendation

Build SelectIQ as a local-first, modular Python/React research application.

Use pretrained image-text embeddings to represent photographs and creative briefs.

Develop a lightweight project-specific pairwise preference model.

Use active learning to choose informative comparisons.

Use a redundancy-aware collection optimizer to select the requested number of photographs.

Add multimodal reasoning selectively for nuanced creative interpretation and explanations.

Validate every generated proposal deterministically.

Keep the entire workflow local where practical, with optional external model services behind a configurable adapter.

**The most important technical work is not the upload interface or the pretrained image encoder. It is the design and evaluation of the preference-learning loop and its translation into a coherent final collection.**

Those components should receive the greatest engineering and research attention.

---

# 29. Final Open Technical Decisions

The following choices remain pending actual development-machine benchmarks and prototype experiments:

1. Exact OpenCLIP checkpoint and feature representation.
2. Maximum safe inference batch size on the development Mac.
3. Whether a hosted multimodal model is needed for reliable creative interpretation.
4. How to translate unrestricted creative briefs into robust model signals.
5. The best regularization and dimensionality reduction for small-sample preferences.
6. The most informative adaptive comparison strategy.
7. The relative weighting of learned preferences, brief relevance, technical evidence, and redundancy.
8. The uncertainty estimation method and review threshold.
9. Performance and memory limits for the selected Apple Silicon machine.
10. The budget-compatible model configuration for the final demonstration.

These are deliberate experimental decisions, not missing product requirements.

**The recommended next action is Phase 0 followed by an image-processing and preference-learning proof of concept.**
