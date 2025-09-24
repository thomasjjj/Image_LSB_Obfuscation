#!/usr/bin/env python3
"""Utility helpers for preparing the secure image processing workspace."""

from __future__ import annotations

from pathlib import Path
from typing import List

from src.DatabaseManager import DatabaseManager


BASE_DIR = Path(__file__).resolve().parent
"""Project root directory used for resolving setup paths."""

REQUIRED_DIRECTORIES = ("src", "ingest", "clean", "originals", "db", "logs")
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

    ingest_readme = base_dir / "ingest" / "README.txt"

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

    db_path = base_dir / "db" / "processing.db"
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

