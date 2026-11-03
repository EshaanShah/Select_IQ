import hashlib
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from selectiq.domain.errors import ImportValidationError


@dataclass(frozen=True, slots=True)
class StagedImage:
    temporary_path: Path
    original_filename: str
    safe_filename: str
    content_hash: str
    width: int
    height: int
    byte_size: int


class ImageStore(Protocol):
    def stage_upload(
        self, project_id: str, original_filename: str, source: BinaryIO
    ) -> StagedImage: ...

    def finalize(self, project_id: str, photo_id: str, staged: StagedImage) -> Path: ...

    def discard(self, path: Path) -> None: ...

    def create_thumbnail(self, project_id: str, photo_id: str) -> Path: ...

    def export_filename_list(self, project_id: str, filenames: list[str]) -> Path: ...


class LocalImageStore:
    chunk_size = 1024 * 1024

    def __init__(self, data_root: Path, max_file_size_bytes: int, max_decoded_pixels: int):
        self.data_root = data_root
        self.max_file_size_bytes = max_file_size_bytes
        self.max_decoded_pixels = max_decoded_pixels

    def stage_upload(
        self, project_id: str, original_filename: str, source: BinaryIO
    ) -> StagedImage:
        suffix = Path(original_filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg"}:
            raise ImportValidationError(
                "unsupported_file_type", "Only .jpg and .jpeg photographs are supported."
            )

        safe_filename = self._safe_filename(original_filename)
        incoming = self.data_root / "projects" / project_id / ".incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        temporary_path = incoming / f"{uuid4()}.part"
        digest = hashlib.sha256()
        byte_size = 0

        try:
            source.seek(0)
            with temporary_path.open("wb") as destination:
                while chunk := source.read(self.chunk_size):
                    byte_size += len(chunk)
                    if byte_size > self.max_file_size_bytes:
                        raise ImportValidationError(
                            "file_too_large",
                            f"The photograph exceeds the {self.max_file_size_bytes // (1024 * 1024)} MB limit.",
                        )
                    digest.update(chunk)
                    destination.write(chunk)

            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(temporary_path) as image:
                        if image.format != "JPEG":
                            raise ImportValidationError(
                                "invalid_jpeg", "The file is not encoded as a JPEG photograph."
                            )
                        width, height = image.size
                        if width * height > self.max_decoded_pixels:
                            megapixels = self.max_decoded_pixels / 1_000_000
                            raise ImportValidationError(
                                "pixel_limit_exceeded",
                                f"The photograph exceeds the {megapixels:g} megapixel limit.",
                            )
                        image.verify()
            except ImportValidationError:
                raise
            except (Image.DecompressionBombError, Image.DecompressionBombWarning):
                megapixels = self.max_decoded_pixels / 1_000_000
                raise ImportValidationError(
                    "pixel_limit_exceeded",
                    f"The photograph exceeds the {megapixels:g} megapixel limit.",
                ) from None
            except (OSError, UnidentifiedImageError):
                raise ImportValidationError(
                    "invalid_jpeg", "The JPEG could not be decoded and may be corrupt."
                ) from None

            return StagedImage(
                temporary_path=temporary_path,
                original_filename=original_filename,
                safe_filename=safe_filename,
                content_hash=digest.hexdigest(),
                width=width,
                height=height,
                byte_size=byte_size,
            )
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def finalize(self, project_id: str, photo_id: str, staged: StagedImage) -> Path:
        photo_directory = self.data_root / "projects" / project_id / "sources" / photo_id
        photo_directory.mkdir(parents=True, exist_ok=False)
        final_path = photo_directory / staged.safe_filename
        try:
            staged.temporary_path.replace(final_path)
        except Exception:
            shutil.rmtree(photo_directory, ignore_errors=True)
            staged.temporary_path.unlink(missing_ok=True)
            raise
        return final_path

    def discard(self, path: Path) -> None:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
                parent = path.parent
                if parent.name != ".incoming":
                    parent.rmdir()

    def create_thumbnail(self, project_id: str, photo_id: str) -> Path:
        raise NotImplementedError("Thumbnail creation belongs to the analysis workflow.")

    def export_filename_list(self, project_id: str, filenames: list[str]) -> Path:
        raise NotImplementedError("Export belongs to the review workflow.")

    @staticmethod
    def _safe_filename(filename: str) -> str:
        normalized = filename.replace("\\", "/")
        safe = Path(normalized).name.replace("\x00", "_")
        return safe or "upload.jpg"

