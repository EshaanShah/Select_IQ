class SelectIQError(Exception):
    """Base error for expected Alpha workflow failures."""


class ValidationError(SelectIQError):
    """Raised when user-supplied project data violates an Alpha rule."""


class ProjectNotFoundError(SelectIQError):
    """Raised when a project ID does not belong to a stored project."""

