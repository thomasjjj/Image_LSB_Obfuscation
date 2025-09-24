#!/usr/bin/env python3
"""
Secure Image Processing Pipeline for Human Rights Documentation

Interactive system that processes images through an auditable pipeline:
1. Images placed in ingest/ folder
2. Secure obfuscation applied (LSB randomization, metadata stripping)
3. Clean images saved to clean/ folder
4. Originals preserved in originals/ folder
5. Full audit trail stored in SQLite database

Pure Python implementation - no external tools required.
"""

import os
import sys
import json
import shutil
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import time

# Image processing imports
from PIL import Image, ImageFilter, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS
import numpy as np
import random
from src.SecureImageProcessor import SecureImageProcessor
from src.DatabaseManager import DatabaseManager
from src.SecurePipeline import SecurePipeline


def load_env_file(env_path: Path) -> None:
    """Load environment variables from a ``.env`` file if present."""

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


def check_setup_required(base_dir: Path):
    """Check if initial setup is required for the configured directories."""

    required_dirs = [
        os.getenv("PIPELINE_INGEST_DIR", "ingest"),
        os.getenv("PIPELINE_CLEAN_DIR", "clean"),
        os.getenv("PIPELINE_ORIGINALS_DIR", "originals"),
        os.getenv("PIPELINE_DB_DIR", "db"),
        os.getenv("PIPELINE_LOG_DIR", "logs"),
        "src",
    ]

    missing_dirs = []
    for dirname in required_dirs:
        if not (base_dir / dirname).exists():
            missing_dirs.append(dirname)

    return missing_dirs


def run_initial_setup(base_dir: Path):
    """Run initial setup if required."""
    print("First-time setup required...")

    try:
        import setup

        if setup.run_setup(base_dir=base_dir):
            print("\nSetup completed successfully!")
            return True
        else:
            print("\nSetup failed. Please check the errors above.")
            return False
    except ImportError:
        # Fallback: basic directory creation
        print("Setup module not found, creating basic directory structure...")
        return create_basic_directories(base_dir)


def create_basic_directories(base_dir: Path):
    """Fallback directory creation if setup.py is not available."""

    directories = [
        os.getenv("PIPELINE_INGEST_DIR", "ingest"),
        os.getenv("PIPELINE_CLEAN_DIR", "clean"),
        os.getenv("PIPELINE_ORIGINALS_DIR", "originals"),
        os.getenv("PIPELINE_DB_DIR", "db"),
        os.getenv("PIPELINE_LOG_DIR", "logs"),
        "src",
    ]

    try:
        for dirname in directories:
            dir_path = base_dir / dirname
            relative_name = dir_path.relative_to(base_dir)
            if dir_path.exists():
                print(f"• {relative_name}/ already exists")
                continue

            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created {relative_name}/")

        # Create basic README for ingest
        ingest_dir = base_dir / os.getenv("PIPELINE_INGEST_DIR", "ingest")
        ingest_readme = ingest_dir / 'README.txt'
        if not ingest_readme.exists():
            ingest_readme.write_text(
                "Place sensitive images here for processing.\n"
                "Supported formats: JPEG, PNG, BMP, TIFF, WebP\n"
            )

        return True
    except Exception as e:
        print(f"Error creating directories: {e}")
        return False


def check_dependencies():
    """Check if required Python packages are available."""
    try:
        import PIL
        import numpy
        return True
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install with: pip install Pillow numpy")
        return False


def show_welcome_message():
    """Display welcome message and basic usage info."""
    print("=" * 60)
    print("SECURE IMAGE PROCESSING PIPELINE")
    print("Human Rights Documentation Tool")
    print("=" * 60)
    print()
    print("This tool securely processes sensitive images by:")
    print("✓ Removing all metadata (EXIF, GPS, etc.)")
    print("✓ Applying LSB randomization to disrupt hidden content")
    print("✓ Preserving originals with complete audit trail")
    print("✓ Creating clean versions safe for distribution")
    print()
    print("Usage:")
    print("1. Place images in the 'ingest/' folder")
    print("2. Run this program and follow the interactive prompts")
    print("3. Collect cleaned images from the 'clean/' folder")
    print()


def main():
    """Main interactive interface with setup check."""

    project_root = Path(__file__).resolve().parent
    load_env_file(project_root / ".env")

    base_dir_env = os.getenv("PIPELINE_BASE_DIR")
    if base_dir_env:
        candidate = Path(base_dir_env).expanduser()
        if candidate.is_absolute():
            base_dir = candidate.resolve()
        else:
            base_dir = (project_root / candidate).resolve()
    else:
        base_dir = project_root

    # Check for required dependencies first
    if not check_dependencies():
        print("\nPlease install required packages and try again.")
        sys.exit(1)

    # Check if setup is required
    missing_dirs = check_setup_required(base_dir)

    if missing_dirs:
        print(f"Missing directories: {', '.join(missing_dirs)}")

        if len(missing_dirs) >= 3:  # If multiple dirs missing, probably first run
            response = input("Run initial setup? (y/n) [y]: ").lower()
            if not response.startswith('n'):
                if not run_initial_setup(base_dir):
                    print("Setup failed. Exiting.")
                    sys.exit(1)

                # Brief pause to let user read setup output
                input("\nPress Enter to continue to main interface...")
        else:
            # Just create missing directories
            print("Creating missing directories...")
            for dirname in missing_dirs:
                dir_path = base_dir / dirname
                dir_path.mkdir(parents=True, exist_ok=True)
                relative_name = dir_path.relative_to(base_dir)
                print(f"✓ Created {relative_name}/")

    # Show welcome message
    show_welcome_message()

    # Initialize pipeline
    try:
        pipeline = SecurePipeline(str(base_dir))
    except Exception as e:
        print(f"Error initializing pipeline: {e}")
        print("Please ensure all required files are present in src/ directory.")
        sys.exit(1)

    # Main interface loop
    while True:
        print(f"Working directory: {pipeline.base_dir.absolute()}")
        print("\nOptions:")
        print("1. Configure and process images")
        print("2. View database summary")
        print("3. Show directory structure")
        print("4. Run setup again")
        print("5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            # Configure and process
            if pipeline.get_user_configuration():
                pipeline.run_processing_batch()

        elif choice == "2":
            # Database summary
            pipeline.show_database_summary()

        elif choice == "3":
            # Show directory structure
            print(f"\nDirectory structure in {pipeline.base_dir}:")
            for key in ['ingest', 'clean', 'originals', 'db', 'logs']:
                dir_path = pipeline.directories[key]
                dir_label = pipeline.directory_names[key]
                if dir_path.exists():
                    files = list(dir_path.glob('*'))
                    count = len([f for f in files if f.is_file()])
                    print(f"  {dir_label}/  ({count} files)")
                else:
                    print(f"  {dir_label}/  (missing)")

        elif choice == "4":
            # Run setup again
            print("\nRunning setup...")
            run_initial_setup(pipeline.base_dir)

        elif choice == "5":
            print("\nExiting pipeline. Stay safe.")
            break

        else:
            print("Invalid option. Please choose 1-5.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Please report this issue if it persists.")