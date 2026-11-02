from fastapi import FastAPI

from selectiq.api.routes import comparisons, feedback, projects, recommendations


def create_app() -> FastAPI:
    app = FastAPI(title="SelectIQ Alpha API", version="0.1.0")
    app.include_router(projects.router)
    app.include_router(comparisons.router)
    app.include_router(recommendations.router)
    app.include_router(feedback.router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

