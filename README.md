# SelectIQ

SelectIQ is a local, AI-assisted photo-culling research prototype. The Alpha learns project-specific preferences from a creative brief and adaptive A/B comparisons, then proposes a target-sized gallery for photographer review.

## Alpha documentation

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

The Alpha structure is scaffolded. User-story behavior remains intentionally unimplemented so each issue can follow red-green-refactor TDD.

## Local setup

Backend and frontend dependencies are declared but are not vendored into the repository.

```bash
cp .env.example .env
cd backend && python -m venv .venv
cd ../frontend && npm install
```

Use `scripts/dev.sh` after dependencies are installed. Use `scripts/test.sh` to run the available test layers.

Do not commit participant galleries, private photographs, generated embeddings, exports, SQLite files, or credentials.

