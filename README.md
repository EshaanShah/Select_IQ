# SelectIQ

SelectIQ is a local, AI-assisted photo-culling research prototype. The Alpha learns project-specific preferences from a creative brief and adaptive A/B comparisons, then proposes a target-sized gallery for photographer review.

## Alpha documentation

- [Authoritative Alpha scope](ALPHA_SCOPE.md)
- [Product requirements](SelectIQ_PRD.md)
- [Technical design](SelectIQ_TDD.md)
- [Finalized user stories](SelectIQ_User_Stories.md)
- [Repository structure](ALPHA_REPO_STRUCTURE.md)

## Repository layout

- `frontend/`: React and TypeScript photographer workflow.
- `backend/`: FastAPI entry point, domain modules, intelligence boundaries, and Python tests.
- `tests/`: cross-application end-to-end tests and sports/retirement fixture manifests.
- `scripts/`: local development, test, benchmark, and comparison-simulation commands.
- `var/`: ignored local projects, model cache, exports, and SQLite state.

## Development status

A-01 gallery ingestion is complete. The remaining Alpha work follows A-02 through A-10 for a 10–30-photo local vertical slice; the 300-photo research workflow is Beta/later scope.

## Local setup

Backend and frontend dependencies are declared but are not vendored into the repository.

```bash
cp .env.example .env
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -e 'backend[dev]'
npm --prefix frontend install
python3 -m alembic -c backend/alembic.ini upgrade head
```

Use `scripts/dev.sh` after dependencies are installed. Use `scripts/test.sh` to run the available test layers.

## AI feature analysis

Gallery analysis uses OpenCLIP `ViT-B-32` with the `laion2b_s34b_b79k` checkpoint. The
model runs on Apple Metal when PyTorch reports MPS support and otherwise falls back to CPU.
Weights are downloaded to the normal machine-level model cache, while normalized image and
prompt embeddings are stored under ignored `var/cache/` paths. Re-running analysis validates
and reuses those artifacts; failed photographs remain visibly failed and can be retried.

Run the deterministic suite with `scripts/test.sh`. The real-model gate generates its own
synthetic JPEG and can download the configured checkpoint:

```bash
SELECTIQ_RUN_REAL_MODEL_TESTS=1 \
  PYTHONPATH=backend/src backend/.venv/bin/python -m pytest \
  backend/tests/integration/test_openclip_smoke.py -m real_model -v
```

For a permissioned local gallery, compare cold and cached performance without committing the
photographs or embeddings:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python scripts/benchmark_gallery.py /path/to/gallery
```

Do not commit participant galleries, private photographs, generated embeddings, exports, or credentials.

