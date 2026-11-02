from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    data_root: Path = Path("var")
    fixture_root: Path = Path("private-fixtures")
    database_path: Path = Path("var/selectiq.sqlite3")
    max_gallery_size: int = 300
    comparison_budget: int = 30
    model_adapter: str = "fake"

    def ensure_runtime_directories(self) -> None:
        self.data_root.mkdir(parents=True, exist_ok=True)
        for directory in ("projects", "cache", "exports"):
            (self.data_root / directory).mkdir(parents=True, exist_ok=True)

