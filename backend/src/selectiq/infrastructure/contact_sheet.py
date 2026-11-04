"""Labeled contact sheets so a whole Alpha gallery fits a vision model's image limit."""

import math
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

TILE = 320
LABEL_HEIGHT = 44
COLUMNS = 4
BACKGROUND = (24, 26, 25)


class ContactSheetError(ValueError):
    pass


def build_contact_sheets(
    items: Sequence[tuple[str, Path]], per_sheet: int = 12, max_sheets: int = 3
) -> list[bytes]:
    """Render (label, path) pairs into JPEG grids, each tile captioned with its label."""
    if not items:
        raise ContactSheetError("At least one photograph is required for a contact sheet.")
    if len(items) > per_sheet * max_sheets:
        raise ContactSheetError(
            f"{len(items)} photographs exceed the {per_sheet * max_sheets}-photo contact sheet limit."
        )
    font = ImageFont.load_default(size=30)
    return [
        _render(items[start : start + per_sheet], font)
        for start in range(0, len(items), per_sheet)
    ]


def _render(items: Sequence[tuple[str, Path]], font) -> bytes:
    columns = min(COLUMNS, len(items))
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * TILE, rows * (TILE + LABEL_HEIGHT)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate(items):
        x = (index % columns) * TILE
        y = (index // columns) * (TILE + LABEL_HEIGHT)
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((TILE - 8, TILE - 8))
        sheet.paste(image, (x + (TILE - image.width) // 2, y + (TILE - image.height) // 2))
        draw.rectangle((x, y + TILE, x + TILE - 1, y + TILE + LABEL_HEIGHT - 1), fill="white")
        draw.text((x + TILE // 2, y + TILE + LABEL_HEIGHT // 2), label, fill="black", font=font,
                  anchor="mm")
    output = BytesIO()
    sheet.save(output, format="JPEG", quality=85)
    return output.getvalue()
