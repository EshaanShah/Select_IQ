# SelectIQ Alpha — guided demo (A-09)

This guide runs the complete Alpha flow on a local Apple Silicon Mac. It works for a facilitator rehearsing the demo and for a participant testing SelectIQ:

**upload → brief and target → AI analysis → 5 A/B choices → AI-informed proposal → remove → export**

The step guide at the top of the app tracks each stage.

## 1. One-time setup

```bash
cp .env.example .env
uv venv --python 3.12 backend/.venv        # or: python3.12 -m venv backend/.venv
uv pip install --python backend/.venv/bin/python -e 'backend[dev]'
npm --prefix frontend ci
npm ci && npx playwright install chromium  # only for the automated end-to-end tests
```

Choose a mode in `.env`:

| Mode | `.env` | What the proposal says |
|---|---|---|
| **Real AI** (participant demo) | `SELECTIQ_MODEL_ADAPTER=openclip`, `SELECTIQ_REASONER=groq`, `GROQ_API_KEY=…` (free key from console.groq.com) | **AI-informed proposal**: OpenCLIP ViT-B-32 brief relevance, Groq guidance, N saved choices |
| Real CLIP, Groq unavailable | As above, but with no key, or the Groq call fails | **Partially AI-informed**: "AI interpretation unavailable — using basic relevance" |
| Offline rehearsal | `SELECTIQ_MODEL_ADAPTER=fake`, `SELECTIQ_REASONER=fake` | **Test signals, not AI** |

The first real analysis downloads the OpenCLIP weights, about 600 MB, into the normal model cache. In real-AI mode, **contact sheets of the photos are sent to Groq**, so use only photographs you have permission to share.

## 2. Prepare a gallery

- **Participant run:** 10–30 permissioned JPEGs (15–20 is ideal), kept outside the repository.
- **Rehearsal run:** a deterministic synthetic gallery, identical on every run:

  ```bash
  backend/.venv/bin/python scripts/make_demo_gallery.py --out ~/selectiq-demo-gallery --count 18
  ```

  This writes 18 labeled JPEGs plus `invalid/corrupt.jpg` and `invalid/notes.png`, so you can try the error messages.

## 3. Start SelectIQ

```bash
scripts/dev.sh        # applies migrations, starts the API on :8000 and the app on :5173
```

Open <http://localhost:5173>.

## 4. Walk through the flow

| Step | Do this | You should see |
|---|---|---|
| 1. Upload | **Choose files** or **Choose folder**, then **Import selected photographs** | "18 photos accepted". Invalid files are listed under "Files that need attention" with a reason |
| 2. Brief and target | Write the creative brief, set **Target number of photographs** to 5, then **Save brief and target** | "Brief and target saved." |
| 3. AI analysis | **Analyze gallery** | Progress, then the AI brief interpretation. Its summary, descriptors, and top photos appear with "Interpreted by …". Wait for this before generating |
| 4. A/B choices | **Start comparisons**, then pick the stronger photo 5 times | "Comparison N of 5", then "Comparison session complete". The guide shows "Done: 5 of 5 choices" |
| 5. Proposal | **Generate proposal** | 5 ranked thumbnails and "5 of 5 selected", with a provenance note (see the mode table) that ends "Based on 5 saved choices." |
| 6. Remove | **Remove** on any card | The card greys out with a "Removed" badge, and the count reads "4 of 5 selected". Nothing replaces it, and **Undo** restores it |
| 7. Export | **Export CSV (4 photos)** | `selectiq-…-vN.csv` with `photo_id,original_filename` for exactly the 4 remaining photos |

To see that your choices matter, generate once before the A/B step and once after. With the synthetic gallery and offline adapters, the top 5 changes.

**Reproducibility:** the same files, brief, and choices give the same proposal in a fresh project. Open a private window, or clear the site's local storage, to start one. The same gallery always shows the same A/B pairs, and only the generated photo IDs differ.

## 5. Automated checks

```bash
scripts/test.sh                                   # backend pytest, frontend vitest, Playwright
npx playwright test                               # end-to-end only, offline adapters
SELECTIQ_E2E_REAL_AI=1 GROQ_API_KEY=… npx playwright test   # real OpenCLIP + Groq run
```

Playwright starts its own API on :8765, with a fresh temporary database, and its own app on :5174. It never touches `var/` or a running dev server. The offline scenarios are:

- **Happy path:** upload → brief and target → analysis → 5 choices → proposal → remove → export, plus CSV checks. The proposal must change after the choices.
- **Failure paths:** corrupt and unsupported files, a target that's too large, the API being unreachable, then recovery.
- **Reproducibility:** two fresh projects produce the same proposals and the same CSV filenames.

The real-AI scenario expects "AI-informed proposal" with ViT-B-32 and Groq.

## 6. Troubleshooting

| Message | Cause and fix |
|---|---|
| "SelectIQ cannot reach its local API at http://localhost:8000…" | The API isn't running. Start `scripts/dev.sh`. Your saved project is kept and reloads once the API is back |
| "AI analysis or interpretation is still running. Try again when it finishes." | Wait for the interpretation panel to finish, then generate |
| "Analyze the gallery before generating a proposal." | Run step 3 first |
| "Only N photographs finished analysis…" | Some photos failed analysis. **Retry analysis**, or lower the target |
| "AI interpretation unavailable — using basic relevance" | Groq failed: no key, a rate limit, or a timeout. Use **Retry AI interpretation**, then generate again |
| A CORS error in the browser console | Usually a 500 from the API. Check the API terminal; an un-migrated database is the most common cause (`scripts/dev.sh` migrates on start) |
