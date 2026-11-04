# Gallery review

Owns A-07 and A-08: generating the target-sized proposal, then reviewing, removing, and exporting it.

- `ProposalPanel.tsx`: appears after AI analysis completes and a brief target is saved. It generates from the saved target, restores the latest proposal on load, and warns when the saved target changed.
  - Its provenance note reads **AI-informed proposal**, **Partially AI-informed** (Groq guidance unavailable), or **Test signals, not AI**, and states how many saved choices were used.

All ranking happens in the backend (`application/proposal_signals.py` and `intelligence/curator.py`). This feature only renders API results.
