#!/usr/bin/env python3
"""Utility helpers for preparing the secure image processing workspace."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from src.DatabaseManager import DatabaseManager


BASE_DIR = Path(__file__).resolve().parent
"""Project root directory used for resolving setup paths."""


def _load_env_file(env_path: Path) -> None:
    """Populate ``os.environ`` with values from a ``.env`` file if present."""

    if not env_path.exists():
        return

    try:
        with env_path.open("r", encoding="utf-8") as env_file:
            for line in env_file:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue

                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip()

                if (value.startswith("'") and value.endswith("'")) or (
                    value.startswith('"') and value.endswith('"')
                ):
                    value = value[1:-1]

                os.environ.setdefault(key, value)
    except OSError as exc:
        print(f"Warning: unable to read environment file {env_path}: {exc}")


_load_env_file(BASE_DIR / ".env")


PIPELINE_DIRECTORIES: Dict[str, str] = {
    'ingest': os.getenv("PIPELINE_INGEST_DIR", "ingest"),
    'clean': os.getenv("PIPELINE_CLEAN_DIR", "clean"),
    'originals': os.getenv("PIPELINE_ORIGINALS_DIR", "originals"),
    'db': os.getenv("PIPELINE_DB_DIR", "db"),
    'logs': os.getenv("PIPELINE_LOG_DIR", "logs"),
}

REQUIRED_DIRECTORIES = ("src",) + tuple(PIPELINE_DIRECTORIES.values())
"""Directories that must exist for the pipeline to operate correctly."""


def check_setup_required(base_dir: Path = BASE_DIR) -> List[str]:
    """Return a list of required directories that are missing."""

    missing: List[str] = []
    for directory in REQUIRED_DIRECTORIES:
        if not (base_dir / directory).exists():
            missing.append(directory)
    return missing


def _ensure_required_directories(base_dir: Path = BASE_DIR) -> None:
    """Create the standard directory structure if it is absent."""

    for directory in REQUIRED_DIRECTORIES:
        path = base_dir / directory

        if directory == "src":
            if not path.exists():
                raise FileNotFoundError(
                    "Required directory 'src' is missing from the project root."
                )
            print(f"• {directory}/ already exists")
            continue

        if path.exists():
            print(f"• {directory}/ already exists")
            continue

        path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {directory}/")


def _write_ingest_readme(base_dir: Path = BASE_DIR) -> None:
    """Create a helper README in the ingest directory if absent."""

    ingest_readme = base_dir / PIPELINE_DIRECTORIES['ingest'] / "README.txt"

    if ingest_readme.exists():
        print(f"• {ingest_readme.relative_to(base_dir)} already exists")
        return

    ingest_readme.write_text(
        "Place sensitive images here for processing.\n"
        "Supported formats: JPEG, PNG, BMP, TIFF, WebP\n"
    )
    print(f"✓ Created {ingest_readme.relative_to(base_dir)}")


def _initialize_database(base_dir: Path = BASE_DIR) -> None:
    """Ensure the SQLite database structure exists."""

    db_filename = os.getenv("PIPELINE_DB_FILENAME", "processing.db")
    db_path = base_dir / PIPELINE_DIRECTORIES['db'] / db_filename
    DatabaseManager(str(db_path))
    print(f"✓ Database initialized at {db_path.relative_to(base_dir)}")


def run_setup(base_dir: Path = BASE_DIR) -> bool:
    """Perform the full initial setup sequence."""

    print("Setting up secure image processing workspace...\n")

    try:
        _ensure_required_directories(base_dir)
        _write_ingest_readme(base_dir)
        _initialize_database(base_dir)
    except Exception as exc:  # noqa: BLE001 - show detailed failure reason
        print(f"Setup failed: {exc}")
        return False

    print("\nSetup completed successfully!")
    return True


def run_initial_setup(base_dir: Path = BASE_DIR) -> bool:
    """Compatibility wrapper used by :mod:`main` for first-time setup."""

    print("First-time setup required...\n")
    return run_setup(base_dir)


def main() -> None:
    """Entry point when executing ``setup.py`` directly."""

    if not run_setup():
        raise SystemExit(1)


if __name__ == "__main__":
    main()

