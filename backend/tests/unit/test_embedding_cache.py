import numpy as np
import pytest

from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache, validate_embedding


def test_cache_round_trip_normalizes_and_rejects_corruption(tmp_path) -> None:
    cache = NumpyEmbeddingCache(tmp_path)
    path = cache.image_path("model", "content")

    saved = cache.save(path, np.array([3.0, 4.0], dtype=np.float32))

    assert saved.dtype == np.float32
    assert np.isclose(np.linalg.norm(saved), 1.0)
    assert np.allclose(cache.load(path, 2), saved)
    path.write_bytes(b"not a numpy artifact")
    assert cache.load(path, 2) is None


def test_embedding_validation_rejects_nonfinite_and_zero_vectors() -> None:
    for invalid in (np.array([np.nan, 1.0]), np.array([np.inf, 1.0]), np.zeros(2)):
        try:
            validate_embedding(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid embedding was accepted")


def test_failed_atomic_replace_leaves_no_valid_artifact(tmp_path, monkeypatch) -> None:
    cache = NumpyEmbeddingCache(tmp_path)
    path = cache.image_path("model", "content")

    def fail_replace(*_args) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr("selectiq.infrastructure.embedding_cache.os.replace", fail_replace)
    with pytest.raises(OSError, match="replace failure"):
        cache.save(path, np.array([1.0, 2.0], dtype=np.float32))

    assert not path.exists()
    assert list(path.parent.glob("*.tmp")) == []
