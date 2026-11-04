import os

import numpy as np
import pytest
from PIL import Image, ImageDraw

from selectiq.infrastructure.model_adapters import OpenClipVisualEncoder


@pytest.mark.real_model
def test_openclip_image_and_text_share_a_finite_normalized_space(tmp_path) -> None:
    if os.getenv("SELECTIQ_RUN_REAL_MODEL_TESTS") != "1":
        pytest.skip("Set SELECTIQ_RUN_REAL_MODEL_TESTS=1 to load real OpenCLIP weights")
    path = tmp_path / "synthetic-celebration.jpg"
    image = Image.new("RGB", (320, 240), "#d99262")
    draw = ImageDraw.Draw(image)
    draw.ellipse((80, 40, 240, 200), fill="#f4d35e", outline="#593c2f", width=8)
    image.save(path, "JPEG")
    encoder = OpenClipVisualEncoder("ViT-B-32", "laion2b_s34b_b79k")

    image_vector = encoder.encode_images([path])[0]
    text_vector = encoder.encode_text("a warm celebration")

    assert image_vector.shape == text_vector.shape
    assert np.isfinite(image_vector).all() and np.isfinite(text_vector).all()
    assert np.isclose(np.linalg.norm(image_vector), 1.0, atol=1e-4)
    assert np.isclose(np.linalg.norm(text_vector), 1.0, atol=1e-4)
    assert np.isfinite(float(image_vector @ text_vector))
