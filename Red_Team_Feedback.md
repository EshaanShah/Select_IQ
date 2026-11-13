# SelectIQ Alpha: Gap Report

**Focus:** Two critical issues in the photo import and AI proposal flows

**How these were verified:** Each finding was reproduced against a running copy of the SelectIQ backend, using its built-in offline test models. Existing tests pass: 267 backend and 53 frontend.

## Summary

| | Issue | Impact | Fix effort |
|---|---|---|---|
| **A** | The product only works for galleries of up to about 30 photos | Photographers with real shoots (1,000+ photos) can't use it | Large: redesign the AI step |
| **B** | Inputs aren't checked early, and AI runs even when there's nothing to choose | Wasted time and AI calls, misleading results | Small: a few validation rules |

## Issue A: Built for 30 photos, but photographers have thousands

### The problem
SelectIQ is meant for photographers, and a single wedding or event shoot can have 1,000–5,000 photos. The app accepts at most **30 photos** per project.

This isn't just a setting someone forgot to raise. The AI step sends the whole gallery to the language model in **one request**. That request can hold at most **3 images**, and each image is a contact sheet of **12 photos**. So the AI can never see more than 36 photos.

### What we found
We raised the limit to 1,000 photos and tested:

| Photos uploaded | Did the AI step work? | What the user gets |
|---|---|---|
| 36 | ✅ Yes | AI-guided proposal |
| **37** | ❌ **No** (`contact_sheet_failed`) | Falls back to basic image-matching only |
| 500 | ❌ No | Falls back to basic image-matching only |

So **the AI breaks at 37 photos**, and it fails silently: the user still gets a proposal, but without the AI guidance.

### Why it matters
- The intended user can't use the product as designed.
- Even the planned Beta target of about 300 photos isn't possible with the current design.
- Other parts aren't built for volume either: one background worker, a SQLite database, and only 20 AI calls per project.

### Recommended fix
Replace the single AI call with a **funnel**:

1. **Score every photo cheaply.** Run the image model and a quality check on all photos as a background job, with a progress bar.
2. **Group similar shots.** Cluster burst and near-duplicate photos, and keep the best frame from each group.
3. **Send only a shortlist to the AI,** in batches of 36 or fewer, then merge the results.
4. **Scale the AI-call budget** with gallery size, and upload large galleries in chunks.
5. **Load-test** at 1,000 and 5,000 photos.

## Issue B: Inputs aren't checked early, and AI runs when there's no choice to make

### The problem
The app checks some limits too late and others not at all. It also runs the full AI analysis in cases where the answer is already obvious.

### What we found

| What we tried | What happened | What should happen |
|---|---|---|
| Uploaded **560 photos** at once | 30 accepted, 530 rejected, but **every file was read, decoded and saved before being thrown away**. 530 error messages were stored. | Stop at the 30-photo limit *before* processing any extra files. |
| **1 photo**, asked for 1, brief "photo of a forest" | Full image analysis plus an AI call ran, and it "selected" the one unrelated photo. | Don't run AI; just return the photo. Also warn that nothing matches "forest". |
| **30 photos**, asked for all 30 | Full image analysis plus an AI call ran to return every photo. | Don't run AI; return all 30. |
| Brief of `ddddddddddd`, `!!!!`, or 200,000 characters | All accepted. Long briefs are silently cut off after about 77 tokens. | Reject or warn. |

### Why it matters
- **Wasted AI calls.** Each project only gets 20, and trivial cases use them up.
- **Wasted time.** Users wait for an analysis that changes nothing.
- **Misleading results.** The output is labeled an AI proposal even when no real choice was made.
- **Wasted work on uploads.** Processing hundreds of extra full-size photos before rejecting them could mean gigabytes of disk work.

### Recommended fix
1. **Skip AI when there's nothing to choose.** If the gallery has 1 photo, or the target equals the number of photos, return every photo right away, labeled *"All photos selected: no AI analysis needed."*
2. **Only run AI ranking when there's a real choice:** at least 2 photos, and a target that's at least 1 and smaller than the number of photos.
3. **Check the upload count first.** Trim the selection to the remaining space in the browser, show a warning, and have the server reject oversized batches before reading them.
4. **Validate the brief:** 3–500 characters, must contain real words, and warn if no photo matches it well.

## Tests to Add

| Issue | Test |
|---|---|
| A | Galleries of 37, 300 and 1,000 photos still get AI-guided proposals, within a set time limit |
| B | With 1 photo, or when every photo is selected, no AI or analysis call is made and the result is labeled correctly |
| B | A batch larger than the remaining space is rejected before any file is processed |
| B | Gibberish, too-short and too-long briefs are rejected with a clear message |


# SelectIQ Alpha: Test Summary

**Product:** An AI-assisted photo culling tool. The user uploads 10–30 JPEGs, writes a creative brief, picks a target count (K), makes about 5 A/B preference choices, reviews an AI-informed proposal of K photos, removes any they don't want, and exports a CSV of the remaining filenames.

## 1. Core Use Cases and Test Status

| Story | Use case | Observed status |
|---|---|---|
| A-01 | Gallery upload (10–30 JPEGs, reject invalid files, unique IDs) | ⚠️ Single-file or multi-select upload is assumed to work. **Folder upload doesn't work.** |
| A-01 / UI | Photo preview in upload | ❌ **Can't close or exit the photo view** after opening it |
| A-02 | Creative brief and target K | ⚠️ Blank input may be rejected, but **gibberish is accepted** (e.g. `ddddddddddd`), so there's no check that the brief means anything |
| A-03 / A-04 | AI feature extraction and brief interpretation | ✅ Images are sent to the AI model. ⚠️ Whether the AI guidance *measurably* changes the selection hasn't been verified. |
| A-05 / A-06 | Pairwise feedback and preference update | ❓ Not tested: repeated pairs blocked, losers stay eligible, reproducible with a fixed seed |
| A-07 | Proposal of exactly K distinct photos | ❓ Not tested: exact count, no duplicates, deterministic output |
| A-08 | Review, remove, and export CSV | ❌ **Nothing can be downloaded**, so export is broken |
| — | Persistence | ✅ Data persists across reloads |
| — | Starting a new session | ⚠️ **"Start New" erases the previous project's data** instead of keeping projects separate |
| A-09 | End-to-end demo | ❌ Blocked by the export failure |
| A-10 | Satisfaction rating (1–5 plus comment) | ❓ Not tested |
| Limits | Photo count limits (<10, >30, large files) | ❓ **Not tested**: the upper and lower bounds haven't been tried |

## 2. System Architecture and Flow

```
[React / JavaScript frontend]
   │  upload JPEGs ─ brief + K ─ A/B choices ─ review grid ─ export CSV
   ▼
[Backend / API proxy]  ← holds the API key server-side (not exposed to the client ✅)
   │  sends images + brief
   ▼
[Groq-hosted API (noted as "Grok") → Qwen multimodal model]
   │  returns structured guidance (scores / photo IDs)
   ▼
[Ranking: prompt relevance + AI guidance + A/B preferences] → top-K proposal
   │
[Local session storage]  ← persists project state; currently overwritten by "Start New"
```

**Flow:** Upload → Brief/K → AI analysis → 5 A/B picks → Proposal (K photos) → Remove → Export CSV → Rating

## 3. Critical and Fragile Areas

1. **Export/download (highest priority).** This is the final deliverable of the flow. Because it's broken, A-08 and the A-09 end-to-end demo can't pass.
2. **Data loss on "Start New."** Starting a new project wipes the old one. This conflicts with A-06's per-project isolation and risks losing a tester's work in the middle of the demo.
3. **Input validation.** Nonsense briefs reach the LLM, which wastes calls and can produce meaningless guidance. The checks on K's range (1 to the photo count) also need confirming.
4. **AI integration.** This covers dependence on an external API (latency, rate limits, outages), parsing structured output, and checking that the model returns photo IDs that actually exist. Errors must show up as errors, not as fake success.
5. **Image payload size.** The photo limit is untested. Sending 30 full-size JPEGs to the model may hit token or request size limits or time out. Images should be resized before sending.
6. **Upload UX.** A failing folder upload and a photo view with no way out are likely to block real testers during the demo.
7. **Determinism and reproducibility.** These are required for the seeded demo (A-06, A-07, A-09) but haven't been verified. LLM output is non-deterministic unless the temperature is set to 0 or the responses are cached.
8. **API key handling.** The key is safe now. Keep it server-side and out of the repo and the frontend bundle as the code changes.


# SelectIQ Alpha: Test Summary

**Product:** An AI-assisted photo culling tool. The user uploads 10–30 JPEGs, writes a creative brief, picks a target count (K), makes about 5 A/B preference choices, reviews an AI-informed proposal of K photos, removes any they don't want, and exports a CSV of the remaining filenames.

## 1. Core Use Cases and Test Status

| Story | Use case | Observed status |
|---|---|---|
| A-01 | Gallery upload (10–30 JPEGs, reject invalid files, unique IDs) | ⚠️ Single-file or multi-select upload is assumed to work. **Folder upload doesn't work.** |
| A-01 / UI | Photo preview in upload | ❌ **Can't close or exit the photo view** after opening it |
| A-02 | Creative brief and target K | ⚠️ Blank input may be rejected, but **gibberish is accepted** (e.g. `ddddddddddd`), so there's no check that the brief means anything |
| A-03 / A-04 | AI feature extraction and brief interpretation | ✅ Images are sent to the AI model. ⚠️ Whether the AI guidance *measurably* changes the selection hasn't been verified. |
| A-05 / A-06 | Pairwise feedback and preference update | ❓ Not tested: repeated pairs blocked, losers stay eligible, reproducible with a fixed seed |
| A-07 | Proposal of exactly K distinct photos | ❓ Not tested: exact count, no duplicates, deterministic output |
| A-08 | Review, remove, and export CSV | ❌ **Nothing can be downloaded**, so export is broken |
| — | Persistence | ✅ Data persists across reloads |
| — | Starting a new session | ⚠️ **"Start New" erases the previous project's data** instead of keeping projects separate |
| A-09 | End-to-end demo | ❌ Blocked by the export failure |
| A-10 | Satisfaction rating (1–5 plus comment) | ❓ Not tested |
| Limits | Photo count limits (<10, >30, large files) | ❓ **Not tested**: the upper and lower bounds haven't been tried |

## 2. System Architecture and Flow

```
[React / JavaScript frontend]
   │  upload JPEGs ─ brief + K ─ A/B choices ─ review grid ─ export CSV
   ▼
[Backend / API proxy]  ← holds the API key server-side (not exposed to the client ✅)
   │  sends images + brief
   ▼
[Groq-hosted API (noted as "Grok") → Qwen multimodal model]
   │  returns structured guidance (scores / photo IDs)
   ▼
[Ranking: prompt relevance + AI guidance + A/B preferences] → top-K proposal
   │
[Local session storage]  ← persists project state; currently overwritten by "Start New"
```

**Flow:** Upload → Brief/K → AI analysis → 5 A/B picks → Proposal (K photos) → Remove → Export CSV → Rating

## 3. Critical and Fragile Areas

1. **Export/download (highest priority).** This is the final deliverable of the flow. Because it's broken, A-08 and the A-09 end-to-end demo can't pass.
2. **Data loss on "Start New."** Starting a new project wipes the old one. This conflicts with A-06's per-project isolation and risks losing a tester's work in the middle of the demo.
3. **Input validation.** Nonsense briefs reach the LLM, which wastes calls and can produce meaningless guidance. The checks on K's range (1 to the photo count) also need confirming.
4. **AI integration.** This covers dependence on an external API (latency, rate limits, outages), parsing structured output, and checking that the model returns photo IDs that actually exist. Errors must show up as errors, not as fake success.
5. **Image payload size.** The photo limit is untested. Sending 30 full-size JPEGs to the model may hit token or request size limits or time out. Images should be resized before sending.
6. **Upload UX.** A failing folder upload and a photo view with no way out are likely to block real testers during the demo.
7. **Determinism and reproducibility.** These are required for the seeded demo (A-06, A-07, A-09) but haven't been verified. LLM output is non-deterministic unless the temperature is set to 0 or the responses are cached.
8. **API key handling.** The key is safe now. Keep it server-side and out of the repo and the frontend bundle as the code changes.
