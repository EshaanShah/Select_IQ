# Gallery review

Owns A-07 and A-08: generating the target-sized proposal, then reviewing, removing, and exporting it.

- `ProposalPanel.tsx`: appears after AI analysis completes and a brief target is saved. It generates from the saved target, restores the latest proposal on load, and warns when the saved target changed.
  - Its provenance note reads **AI-informed proposal**, **Partially AI-informed** (Groq guidance unavailable), or **Test signals, not AI**, and states how many saved choices were used.

- `ReviewGrid.tsx`: a thumbnail grid of every proposed photo in rank order. **Remove** greys a card out without replacing it, and **Undo** restores it. The count reads "N of K selected".

The export link downloads `GET /projects/{id}/recommendations/export`, a CSV with `photo_id,original_filename` for each remaining photo in rank order. Duplicate filenames stay distinguishable by `photo_id`.

All ranking happens in the backend (`application/proposal_signals.py` and `intelligence/curator.py`). This feature only renders API results.
