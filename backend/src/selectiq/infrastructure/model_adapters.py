import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image, ImageOps


class VisualEncoder(Protocol):
    model_name: str
    checkpoint: str
    fingerprint: str
    dimension: int | None

    def encode_images(self, image_paths: Sequence[Path]) -> np.ndarray: ...

    def encode_text(self, text: str) -> np.ndarray: ...


class ModelLoadError(RuntimeError):
    pass


class DeterministicVisualEncoder:
    """Fast test adapter that preserves the production image/text contract."""

    def __init__(self, dimension: int = 8, fail_names: set[str] | None = None):
        self.model_name = "deterministic-test"
        self.checkpoint = "v1"
        self.fingerprint = "deterministic-test-v1"
        self.dimension = dimension
        self.fail_names = fail_names or set()
        self.image_calls = 0
        self.text_calls = 0

    def _vector(self, value: bytes) -> np.ndarray:
        digest = hashlib.sha256(value).digest()
        raw = np.frombuffer(digest, dtype=np.uint8)[: self.dimension].astype(np.float32) + 1.0
        return raw / np.linalg.norm(raw)

    def encode_images(self, image_paths: Sequence[Path]) -> np.ndarray:
        self.image_calls += 1
        vectors = []
        for path in image_paths:
            if path.name in self.fail_names:
                raise RuntimeError(f"Injected inference failure for {path.name}")
            vectors.append(self._vector(path.read_bytes()))
        return np.stack(vectors) if vectors else np.empty((0, self.dimension), dtype=np.float32)

    def encode_text(self, text: str) -> np.ndarray:
        self.text_calls += 1
        return self._vector(text.encode("utf-8"))


class OpenClipVisualEncoder:
    def __init__(
        self,
        model_name: str,
        checkpoint: str,
        device: str = "auto",
        feature_version: str = "1",
    ) -> None:
        self.model_name = model_name
        self.checkpoint = checkpoint
        self.requested_device = device
        self.fingerprint = hashlib.sha256(
            f"openclip:{model_name}:{checkpoint}:rgb-exif-v1:{feature_version}".encode()
        ).hexdigest()[:24]
        self.dimension: int | None = None
        self.device = "cpu"
        self._model = None
        self._preprocess = None
        self._tokenizer = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import open_clip
            import torch

            if self.requested_device == "auto":
                self.device = "mps" if torch.backends.mps.is_available() else "cpu"
            else:
                self.device = self.requested_device
            model, _, preprocess = open_clip.create_model_and_transforms(
                self.model_name, pretrained=self.checkpoint, device=self.device
            )
        except Exception as error:
            raise ModelLoadError(f"Could not load {self.model_name}: {error}") from error
        model.eval()
        self._model = model
        self._preprocess = preprocess
        self._tokenizer = open_clip.get_tokenizer(self.model_name)

    def encode_images(self, image_paths: Sequence[Path]) -> np.ndarray:
        self._load()
        import torch

        tensors = []
        for path in image_paths:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                tensors.append(self._preprocess(image))
        if not tensors:
            return np.empty((0, self.dimension or 0), dtype=np.float32)
        batch = torch.stack(tensors).to(self.device)
        with torch.inference_mode():
            encoded = self._model.encode_image(batch, normalize=True)
        result = encoded.detach().float().cpu().numpy()
        self.dimension = int(result.shape[1])
        return result

    def encode_text(self, text: str) -> np.ndarray:
        if not text.strip():
            raise ValueError("Prompt must not be blank.")
        self._load()
        import torch

        tokens = self._tokenizer([text]).to(self.device)
        with torch.inference_mode():
            encoded = self._model.encode_text(tokens, normalize=True)
        result = encoded[0].detach().float().cpu().numpy()
        self.dimension = int(result.size)
        return result


class BriefReasoner(Protocol):
    def interpret(self, brief: str) -> dict[str, object]: ...

