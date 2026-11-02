from typing import Protocol

from selectiq.domain.models import Project


class ProjectRepository(Protocol):
    def save(self, project: Project) -> None: ...

    def get(self, project_id: str) -> Project | None: ...

