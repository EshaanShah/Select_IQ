"""A-07: proposals combine A-03 relevance, A-04 guidance, and A-06 preferences."""

import hashlib
from io import BytesIO

import pytest
from conftest import AiStack, build_stack, distinct_jpegs

from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.domain.errors import ProjectNotFoundError, ProposalNotFoundError, ValidationError
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder
from selectiq.infrastructure.reasoners import ReasonerError, ScriptedBriefReasoner


def ids(proposal) -> list[str]:
    return [item.photo_id for item in proposal.items]


def names(proposal) -> list[str]:
    return [item.original_filename for item in proposal.items]


def test_generates_and_persists_five_distinct_analyzed_photos_from_eighteen(stack: AiStack) -> None:
    project_id = stack.analyzed_gallery(18)
    service = stack.recommendations()

    proposal = service.generate(project_id)

    gallery = {photo.id for photo in stack.projects.repository.list_photos(project_id)}
    assert proposal.version == 1
    assert proposal.target_count == 5
    assert len(ids(proposal)) == len(set(ids(proposal))) == 5
    assert set(ids(proposal)) <= gallery
    assert service.current(project_id) == proposal


def test_every_real_signal_reaches_the_ranking(stack: AiStack) -> None:
    project_id = stack.analyzed_gallery(18)

    proposal = stack.recommendations().generate(project_id, 18)

    def spread(name: str) -> set[float]:
        return {round(item.contributions[name], 6) for item in proposal.items}

    assert len(spread("prompt_relevance")) > 1
    assert len(spread("ai_guidance")) > 1
    assert spread("preference") == {0.0}
    assert proposal.provenance.guidance_status == "completed"
    assert proposal.provenance.comparisons_used == 0
    assert proposal.parameters["weights"]["preference"] == 0.0


def test_saved_choices_change_the_proposal_and_its_weights(stack: AiStack) -> None:
    project_id = stack.analyzed_gallery(18)
    service = stack.recommendations()
    before = service.generate(project_id)
    proposed = set(ids(before))

    stack.make_choices(
        project_id,
        5,
        prefer=lambda pair: pair.photo_b_id if pair.photo_a_id in proposed else pair.photo_a_id,
    )
    after = service.generate(project_id)

    assert ids(after) != ids(before)
    assert after.provenance.comparisons_used == 5
    assert after.parameters["weights"]["preference"] == pytest.approx(1.0)
    assert any(item.contributions["preference"] != 0.0 for item in after.items)


def test_failed_ai_guidance_falls_back_and_is_reported(project_service, tmp_path) -> None:
    failing = ScriptedBriefReasoner([ReasonerError("rate_limited", "Groq rate limit reached.")])
    stack = build_stack(project_service, tmp_path, reasoner=failing)
    project_id = stack.analyzed_gallery(18)

    proposal = stack.recommendations(genuine_encoder=True, genuine_reasoner=True).generate(
        project_id, 18
    )

    assert all(item.contributions["ai_guidance"] == 0.0 for item in proposal.items)
    assert proposal.provenance.guidance_status == "failed"
    assert proposal.provenance.kind == "partial_ai"
    assert proposal.provenance.is_genuine_ai is False


def test_genuine_adapters_with_completed_guidance_are_ai_informed(stack: AiStack) -> None:
    project_id = stack.analyzed_gallery(10)

    proposal = stack.recommendations(genuine_encoder=True, genuine_reasoner=True).generate(
        project_id
    )

    assert proposal.provenance.kind == "ai_informed"
    assert proposal.provenance.is_genuine_ai is True


def test_test_adapters_are_labeled_as_not_ai(stack: AiStack) -> None:
    proposal = stack.recommendations().generate(stack.analyzed_gallery(10))

    assert proposal.provenance.kind == "test_signals"
    assert proposal.provenance.embedding_model == "deterministic-test / v1"
    assert proposal.provenance.guidance_model == "scripted / scripted-test"


def test_regeneration_creates_a_new_version_with_identical_ranking(stack: AiStack) -> None:
    project_id = stack.analyzed_gallery(18)
    service = stack.recommendations()

    first, second = service.generate(project_id), service.generate(project_id)

    assert second.version == first.version + 1
    assert ids(second) == ids(first)
    assert service.current(project_id).id == second.id


def test_fixed_inputs_reproduce_the_same_proposal_in_a_fresh_project(stack: AiStack) -> None:
    service = stack.recommendations()

    first = service.generate(stack.analyzed_gallery(18))
    second = service.generate(stack.analyzed_gallery(18))

    assert names(first) == names(second)
    assert set(ids(first)).isdisjoint(ids(second))


def test_photos_that_failed_analysis_are_excluded_and_counted(project_service, tmp_path) -> None:
    encoder = DeterministicVisualEncoder(fail_names={"photo-00.jpg", "photo-01.jpg"})
    stack = build_stack(project_service, tmp_path, encoder=encoder)
    project_id = stack.analyzed_gallery(8, target=5)
    service = stack.recommendations()

    proposal = service.generate(project_id, 6)

    assert {"photo-00.jpg", "photo-01.jpg"}.isdisjoint(names(proposal))
    assert proposal.provenance.excluded_photo_count == 2
    with pytest.raises(ValidationError, match="Only 6 photographs finished analysis"):
        service.generate(project_id, 7)


def test_generation_requires_a_brief_and_completed_analysis(stack: AiStack) -> None:
    service = stack.recommendations()
    unbriefed = stack.projects.create_project()
    stack.projects.import_photos(unbriefed.id, [PhotoUpload("a.jpg", BytesIO(distinct_jpegs(1)[0]))])
    with pytest.raises(ValidationError, match="Save a creative brief and target"):
        service.generate(unbriefed.id)

    unanalyzed = stack.projects.create_project()
    stack.projects.import_photos(
        unanalyzed.id, [PhotoUpload(f"{i}.jpg", BytesIO(c)) for i, c in enumerate(distinct_jpegs(3))]
    )
    stack.projects.set_prompt_and_target(unanalyzed.id, "Quiet moments.", 2)
    with pytest.raises(ValidationError, match="Analyze the gallery"):
        service.generate(unanalyzed.id)


def test_invalid_requests_fail_clearly(stack: AiStack) -> None:
    project_id = stack.analyzed_gallery(3, target=2)
    service = stack.recommendations()

    with pytest.raises(ValidationError, match="between 1 and 3"):
        service.generate(project_id, 4)
    with pytest.raises(ProjectNotFoundError):
        service.generate("00000000-0000-0000-0000-000000000000")
    with pytest.raises(ProposalNotFoundError):
        service.current(project_id)


def test_projects_are_isolated(stack: AiStack) -> None:
    first = stack.analyzed_gallery(10, prefix="first")
    second = stack.analyzed_gallery(10, prefix="second")
    service = stack.recommendations()

    proposal = service.generate(first, 10)

    assert all(name.startswith("first-") for name in names(proposal))
    with pytest.raises(ProposalNotFoundError):
        service.current(second)


def test_duplicate_filenames_are_proposed_as_distinct_photos(stack: AiStack) -> None:
    first, second = distinct_jpegs(2)
    project_id = stack.analyzed_gallery(
        target=2,
        uploads=[PhotoUpload("same.jpg", BytesIO(first)), PhotoUpload("same.jpg", BytesIO(second))],
    )

    proposal = stack.recommendations().generate(project_id)

    assert names(proposal) == ["same.jpg", "same.jpg"]
    assert len(set(ids(proposal))) == 2


@pytest.mark.regression
def test_generation_never_modifies_working_copies(
    stack: AiStack, project_service: ProjectService
) -> None:
    project_id = stack.analyzed_gallery(8)
    photos = project_service.repository.list_photos(project_id)

    stack.recommendations().generate(project_id)

    for photo in photos:
        assert hashlib.sha256(photo.working_path.read_bytes()).hexdigest() == photo.content_hash
