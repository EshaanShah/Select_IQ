from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SELECTIQ_", env_file=".env", extra="ignore"
    )

    data_root: Path = Path("var")
    fixture_root: Path = Path("private-fixtures")
    database_url: str = "sqlite:///var/selectiq.sqlite3"
    max_gallery_size: int = Field(default=30, ge=1)
    max_file_size_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    max_decoded_pixels: int = Field(default=60_000_000, ge=1)
    comparison_budget: int = 5
    model_adapter: str = "fake"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def ensure_runtime_directories(self) -> None:
        self.data_root.mkdir(parents=True, exist_ok=True)
        for directory in ("projects", "cache", "exports"):
            (self.data_root / directory).mkdir(parents=True, exist_ok=True)

