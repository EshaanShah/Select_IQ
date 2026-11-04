# 2026-11-04 — A-08 review and export

**Status:** Accepted for Alpha.

## Decision

1. **Removal without replacement.** `DELETE /projects/{id}/recommendations/selection/{photoId}` sets `proposal_items.removed_at` (migration `0007_proposal_item_removal`) on the **latest** proposal. The item stays in the proposal and no other photo is promoted. Removal is idempotent.
2. **Undo.** `POST /projects/{id}/recommendations/selection/{photoId}/restore` clears `removed_at`. You can only restore photos that the proposal originally suggested.
3. **Remove all.** This is allowed. The selection becomes empty, and the export is a header-only CSV.
4. **Regeneration.** Generating again creates a new proposal version with a full K selection. Earlier versions and their removals are kept but no longer shown.
5. **CSV format.** The CSV is UTF-8 with the header `photo_id,original_filename`. It has one row per remaining photo in rank order, quoted per RFC 4180. Original filenames are exported exactly as uploaded. `photo_id` distinguishes duplicate filenames.
6. **Export record.** Each export is also written to `var/exports/{projectId}/selectiq-{projectPrefix}-v{version}.csv`, which is git-ignored. The browser receives the same bytes as an attachment.
7. **Thumbnails.** `GET /projects/{id}/photos/{photoId}/thumbnail` lazily writes a cached thumbnail at most 512 px wide or tall to `var/projects/{id}/thumbnails/`. It returns 404 for photos outside the project. Full-resolution files are never sent to the grid.
8. **Source safety.** Review and export only read the working copies. Regression tests confirm that every working-copy hash still matches its upload hash.

## Consequences

- CORS now allows `DELETE` and exposes `Content-Disposition`.
- An error response (for example, a 500) has no CORS headers, so the browser reports it as a CORS failure. Check the API log for the real cause.
