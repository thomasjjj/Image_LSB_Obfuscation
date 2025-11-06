import shutil
import subprocess
from pathlib import Path
from typing import Dict, Tuple


class SecureVideoProcessor:
    """Handles MP4 processing focused on metadata stripping.

    Notes:
    - This processor performs container-level metadata removal only.
    - No LSB randomization or frame-level perturbation is applied.
    - Requires `ffmpeg` to be available on PATH.
    """

    def __init__(self) -> None:
        pass

    @staticmethod
    def ffmpeg_available() -> bool:
        """Return True if `ffmpeg` binary is available on PATH."""
        return shutil.which("ffmpeg") is not None

    def strip_all_metadata(self, input_path: Path, output_path: Path) -> Tuple[bool, Dict]:
        """Create a new MP4 with all container and stream metadata removed.

        Uses stream copy to avoid re-encoding: `-c copy`.

        Returns (success, details dict).
        """
        details: Dict = {
            "tool": "ffmpeg",
            "operation": "strip_metadata",
            "arguments": [
                "-map", "0",               # keep all streams
                "-map_metadata", "-1",     # drop all metadata (global + stream)
                "-map_chapters", "-1",    # drop chapters
                "-c", "copy",
                "-movflags", "use_metadata_tags",  # ensure clean tags on write
            ],
            "lsb_randomization_applied": False,
        }

        if not self.ffmpeg_available():
            details["error"] = "ffmpeg not found on PATH"
            return False, details

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(input_path),
            *details["arguments"],
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True)
            return True, details
        except subprocess.CalledProcessError as exc:
            details["error"] = str(exc)
            return False, details

