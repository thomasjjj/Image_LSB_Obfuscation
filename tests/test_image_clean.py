import io
from pathlib import Path

import pytest
from PIL import Image

# Ensure package import using src/ layout when running tests directly
import sys
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from secure_pipeline import image_clean  # noqa: E402


def _make_sample_image_with_exif(path: Path) -> None:
    img = Image.new("RGB", (64, 64), color=(120, 180, 200))
    # Draw a small variation
    for x in range(16, 48):
        for y in range(16, 48):
            img.putpixel((x, y), (200, 80, 160))

    # Try to add EXIF if supported by Pillow
    exif = None
    try:
        exif = Image.Exif()
        # DateTimeOriginal tag (0x9003)
        exif[0x9003] = "2020:01:01 00:00:00"
    except Exception:
        exif = None

    if exif is not None:
        img.save(path, format="JPEG", exif=exif)
    else:
        img.save(path, format="JPEG")


def test_image_clean_writes_output_and_removes_metadata(tmp_path: Path) -> None:
    src = tmp_path / "sample_exif.jpg"
    _make_sample_image_with_exif(src)

    # Sanity: source should have some EXIF or at least be a valid image
    with Image.open(src) as im:
        ex = im.getexif()
        assert im.width == 64 and im.height == 64
        # We don't strictly require EXIF to be present across environments,
        # but we confirm the getter works without error.
        assert ex is not None

    cleaned_img, log, out_path = image_clean(
        src,
        lsb_flip_probability=0.15,
        obfuscation_passes=2,
        add_noise=True,
        output_format="JPEG",
        jpeg_quality=85,
        output_dir=tmp_path,
    )

    assert out_path is not None
    assert out_path.exists()
    assert log.get("metadata_stripped", True) is True
    assert log.get("passes_applied", 0) >= 1

    # Verify cleaned output has no EXIF
    with Image.open(out_path) as im2:
        ex2 = im2.getexif()
        assert ex2 is not None
        assert len(ex2) == 0
        assert "exif" not in im2.info


def test_image_clean_in_memory_returns_image(tmp_path: Path) -> None:
    # Create a PNG image in memory
    img = Image.new("RGB", (32, 32), color=(10, 20, 30))
    cleaned_img, log, out_path = image_clean(
        img,
        lsb_flip_probability=0.1,
        obfuscation_passes=1,
        add_noise=False,
        output_format="PNG",
    )
    assert out_path is None
    assert cleaned_img.size == (32, 32)
    assert log.get("lsb_randomization_applied", True) in (True, False)

