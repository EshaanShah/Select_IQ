import hashlib
import json
import os
from io import BytesIO
from pathlib import Path

import pytest

from selectiq.application.project_service import PhotoUpload, ProjectService


@pytest.mark.parametrize("scenario", ["sports", "retirement"])
def test_permissioned_gallery_imports_without_scenario_specific_failures(
    scenario: str, project_service: ProjectService
) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    manifest_path = repository_root / "tests" / "fixtures" / scenario / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    photographs = manifest.get("photographs", [])
    fixture_root = os.getenv("SELECTIQ_FIXTURE_ROOT")
    if not fixture_root or not photographs:
        pytest.skip(f"Permissioned {scenario} manifest/files are not available")

    scenario_root = Path(fixture_root) / manifest["private_fixture_subdirectory"]
    missing = [item["relative_path"] for item in photographs if not (scenario_root / item["relative_path"]).is_file()]
    if missing:
        pytest.skip(f"Permissioned {scenario} files are missing: {', '.join(missing[:3])}")

    source_hashes = {
        item["relative_path"]: hashlib.sha256(
            (scenario_root / item["relative_path"]).read_bytes()
        ).hexdigest()
        for item in photographs
    }
    project = project_service.create_project()
    uploads = [
        PhotoUpload(item["relative_path"], BytesIO((scenario_root / item["relative_path"]).read_bytes()))
        for item in photographs
    ]
    result = project_service.import_photos(project.id, uploads)

    assert result.rejected == []
    assert result.accepted_count == len(photographs)
    assert source_hashes == {
        item["relative_path"]: hashlib.sha256(
            (scenario_root / item["relative_path"]).read_bytes()
        ).hexdigest()
        for item in photographs
    }
