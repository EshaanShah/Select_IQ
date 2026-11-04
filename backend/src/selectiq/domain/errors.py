class SelectIQError(Exception):
    """Base error for expected Alpha workflow failures."""


class ValidationError(SelectIQError):
    """Raised when user-supplied project data violates an Alpha rule."""


class ProjectNotFoundError(SelectIQError):
    """Raised when a project ID does not belong to a stored project."""


class DuplicateComparisonError(ValidationError):
    """Raised when a project submits the same unordered photo pair twice."""


class ImportValidationError(ValidationError):
    """A single uploaded file failed an ingestion rule."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

