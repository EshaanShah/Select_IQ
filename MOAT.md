# SelectIQ Moat

SelectIQ’s advantage is not “AI that picks good photos.” It is **project-specific selection that learns what this photographer wants for this gallery**, then proposes a target-sized cull the photographer still controls.

## What competitors typically optimize for

Most automated cullers lean on generic signals: sharpness, exposure, faces, or one-size aesthetics. Those metrics help with obvious rejects, but they do not know whether a softer frame better matches the story, or whether two near-duplicates should both survive for narrative variety.

## What SelectIQ uniquely combines

1. **Creative brief as editorial intent**  
   Free-text direction is interpreted into favor/avoid visual concepts, not treated as a keyword filter.

2. **Local visual grounding (OpenCLIP)**  
   Every photo is scored in a shared embedding space against the brief and guided descriptors. Scoring stays on-device, cacheable, and comparable across the full gallery.

3. **Bounded generative guidance, not model-as-curator**  
   The vision LLM inspects contact sheets and returns structured notes. Final ranking is computed locally so the system stays deterministic, auditable, and recoverable when the provider fails.

4. **Few adaptive A/B preferences**  
   A small set of pairwise choices teaches project-specific taste. Preferences can override generic quality assumptions; losing photos remain eligible for the final set.

5. **Human-in-the-loop deliverable**  
   The product ends in review, edit, and filename export—not an irreversible auto-pick. Photographer judgment stays authoritative.

## Defensibility in practice

| Moat layer | Why it is hard to copy casually |
|---|---|
| Multi-signal curator | Brief relevance + guided descriptors + preference scores must be fused into exactly-K, reproducible proposals with clear provenance. |
| Preference efficiency | Useful personalization from few comparisons, not a long labeling session. |
| Local-first evidence | Embeddings and ranking stay local; originals are not the default payload to an external model. |
| Research loop | Satisfaction ratings and operational metrics close the loop on whether guidance actually improves culls. |

## One-line summary

**SelectIQ’s moat is learning each project’s editorial taste—brief + local vision + sparse human comparisons—then ranking deterministically under photographer control.**
