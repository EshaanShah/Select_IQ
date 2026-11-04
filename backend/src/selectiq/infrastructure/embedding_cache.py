import os
from pathlib import Path
from uuid import uuid4

import numpy as np


class InvalidEmbeddingError(ValueError):
    pass


def validate_embedding(value: np.ndarray, expected_dimension: int | None = None) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float32)
    if vector.ndim != 1 or vector.size == 0:
        raise InvalidEmbeddingError("Embedding must be a nonempty one-dimensional vector.")
    if expected_dimension is not None and vector.size != expected_dimension:
        raise InvalidEmbeddingError(
            f"Embedding dimension {vector.size} does not match {expected_dimension}."
        )
    if not np.isfinite(vector).all():
        raise InvalidEmbeddingError("Embedding contains a non-finite value.")
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise InvalidEmbeddingError("Embedding has zero norm.")
    vector = vector / norm
    if not np.isclose(np.linalg.norm(vector), 1.0, atol=1e-4):
        raise InvalidEmbeddingError("Embedding could not be normalized.")
    return vector.astype(np.float32, copy=False)


class NumpyEmbeddingCache:
    def __init__(self, root: Path):
        self.root = root

    def image_path(self, fingerprint: str, content_hash: str) -> Path:
        return self.root / "embeddings" / fingerprint / f"{content_hash}.npy"

    def prompt_path(self, fingerprint: str, prompt_hash: str) -> Path:
        return self.root / "prompts" / fingerprint / f"{prompt_hash}.npy"

    def load(self, path: Path, expected_dimension: int | None = None) -> np.ndarray | None:
        if not path.is_file():
            return None
        try:
            with path.open("rb") as source:
                value = np.load(source, allow_pickle=False)
            return validate_embedding(value, expected_dimension)
        except (OSError, ValueError, InvalidEmbeddingError):
            return None

    def save(self, path: Path, value: np.ndarray) -> np.ndarray:
        vector = validate_embedding(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
        try:
            with temporary.open("wb") as destination:
                np.save(destination, vector, allow_pickle=False)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return vector
