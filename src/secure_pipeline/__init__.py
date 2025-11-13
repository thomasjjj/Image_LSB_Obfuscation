from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from .secure_pipeline import SecurePipeline
from .secure_image_processor import SecureImageProcessor
from .secure_video_processor import SecureVideoProcessor
from .database_manager import DatabaseManager

ImageLike = "PIL.Image.Image"  # forward declaration for typing in docstrings


def image_clean(
    source: Union[str, Path, "ImageLike"],
    *,
    lsb_flip_probability: float = 0.15,
    obfuscation_passes: int = 2,
    add_noise: bool = True,
    output_format: str = "JPEG",
    jpeg_quality: int = 85,
    output_dir: Optional[Union[str, Path]] = None,
    filename_suffix: str = "_clean",
) -> Tuple["ImageLike", Dict, Optional[Path]]:
    """Clean a single image by stripping metadata and applying LSB randomization.

    Parameters
    - source: Path to an image file or a loaded Pillow Image instance.
    - lsb_flip_probability: Probability (0.05–0.30 recommended) of flipping LSB bits per pass.
    - obfuscation_passes: Number of LSB randomization passes (1–5).
    - add_noise: Whether to add subtle noise to disrupt patterns.
    - output_format: "JPEG" (recommended, adds compression artifacts) or "PNG".
    - jpeg_quality: JPEG quality when output_format is JPEG (70–95 recommended).
    - output_dir: If provided, saves the cleaned image to this directory and returns its Path.
                  If None, no file is written and the cleaned Pillow Image is returned.
    - filename_suffix: Suffix appended to the stem when saving to a file (default "_clean").

    Returns
    - cleaned_image: Pillow Image object of the cleaned image.
    - obfuscation_log: Dict capturing metadata stripping and obfuscation details.
    - output_path: Path to the saved file if output_dir was provided, otherwise None.
    """
    from PIL import Image  # local import to avoid mandatory dependency when unused

    # Normalize config
    config: Dict = {
        "lsb_flip_probability": float(lsb_flip_probability),
        "obfuscation_passes": int(obfuscation_passes),
        "add_noise": bool(add_noise),
        "output_format": output_format.upper(),
        "jpeg_quality": int(jpeg_quality),
        "operator_name": "API",
    }
    proc = SecureImageProcessor(config)

    # Load or accept input image
    img: Image.Image
    src_path: Optional[Path] = None
    if hasattr(source, "__class__") and source.__class__.__name__ == "Image":
        img = source  # type: ignore[assignment]
    elif hasattr(source, "__class__") and source.__class__.__name__ == "JpegImageFile":
        img = source  # type: ignore[assignment]
    elif hasattr(source, "__class__") and source.__class__.__name__.endswith("ImageFile"):
        img = source  # type: ignore[assignment]
    elif isinstance(source, (str, Path)):
        src_path = Path(source)
        img = Image.open(src_path)
    else:
        # Fallback: try Pillow open
        src_path = Path(str(source))
        img = Image.open(src_path)

    cleaned_img, log = proc.strip_metadata_and_obfuscate(img)

    out_path: Optional[Path] = None
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if src_path is not None:
            stem = src_path.stem
        else:
            stem = "image"
        if config["output_format"] == "JPEG":
            out_name = f"{stem}{filename_suffix}.jpg"
            save_params = {"quality": config["jpeg_quality"], "optimize": True, "progressive": True}
        else:
            out_name = f"{stem}{filename_suffix}.png"
            save_params = {"optimize": True}

        out_path = output_dir / out_name
        cleaned_img.save(out_path, config["output_format"], **save_params)

    return cleaned_img, log, out_path


def video_clean(
    source: Union[str, Path],
    *,
    output_dir: Optional[Union[str, Path]] = None,
    filename_suffix: str = "_clean",
    overwrite: bool = True,
) -> Tuple[Path, Dict]:
    """Strip all MP4 metadata and return the cleaned file path and details.

    Parameters
    - source: Path to an .mp4 file.
    - output_dir: Directory to write the cleaned video; defaults to the source directory.
    - filename_suffix: Suffix appended to the stem for the cleaned filename.
    - overwrite: If True, overwrite existing cleaned file.

    Returns
    - output_path: Path to the cleaned MP4 file.
    - details: Dict with tool/arguments used and flags like lsb_randomization_applied.
    """
    src = Path(source)
    if src.suffix.lower() != ".mp4":
        raise ValueError("Only .mp4 files are supported for video_clean")

    out_dir = Path(output_dir) if output_dir is not None else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src.stem}{filename_suffix}.mp4"

    if out_path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {out_path}")

    vproc = SecureVideoProcessor()
    ok, details = vproc.strip_all_metadata(src, out_path)
    if not ok:
        raise RuntimeError(f"ffmpeg processing failed: {details.get('error','unknown error')}")

    return out_path, details


__all__ = [
    "SecurePipeline",
    "SecureImageProcessor",
    "SecureVideoProcessor",
    "DatabaseManager",
    "image_clean",
    "video_clean",
]
