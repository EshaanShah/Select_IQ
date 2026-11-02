from typing import Protocol, Sequence


class VisualEncoder(Protocol):
    def encode_images(self, image_paths: Sequence[str]) -> Sequence[Sequence[float]]: ...


class BriefReasoner(Protocol):
    def interpret(self, brief: str) -> dict[str, object]: ...

