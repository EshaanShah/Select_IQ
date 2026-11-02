from pathlib import Path
from typing import Protocol


class ImageStore(Protocol):
    def copy_into_project(self, project_id: str, source: Path) -> Path: ...

    def create_thumbnail(self, project_id: str, photo_id: str) -> Path: ...

    def export_filename_list(self, project_id: str, filenames: list[str]) -> Path: ...

