"""A-09: the guided demo never produces a proposal while AI work is still in flight."""

import pytest
from conftest import AiStack

from selectiq.domain.errors import ValidationError


def test_generation_waits_for_running_analysis_or_interpretation(stack: AiStack) -> None:
    project_id = stack.analyzed_gallery(10)
    busy = stack.recommendations(analysis_running=lambda candidate: candidate == project_id)

    with pytest.raises(ValidationError, match="AI analysis or interpretation is still running"):
        busy.generate(project_id)


def test_other_projects_are_not_blocked_by_a_running_job(stack: AiStack) -> None:
    running = stack.analyzed_gallery(10, prefix="running")
    ready = stack.analyzed_gallery(10, prefix="ready")
    service = stack.recommendations(analysis_running=lambda candidate: candidate == running)

    assert len(service.generate(ready).items) == 5
