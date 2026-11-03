from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from selectiq.api.dependencies import get_settings
from selectiq.api.routes import comparisons, feedback, projects, recommendations


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SelectIQ Alpha API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(projects.router)
    app.include_router(comparisons.router)
    app.include_router(recommendations.router)
    app.include_router(feedback.router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

