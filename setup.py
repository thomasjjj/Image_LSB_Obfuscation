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

import sys
from pathlib import Path

# Image processing imports
from src.SecurePipeline import SecurePipeline


def check_setup_required(base_dir: Path = Path("src")):
    """Check if initial setup is required."""
    required_dirs = ['images_ingest', 'images_clean', 'images_originals', 'db', 'src']

    missing_dirs = []
    for dirname in required_dirs:
        if not (base_dir / dirname).exists():
            missing_dirs.append(dirname)

    return missing_dirs


def run_initial_setup():
    """Run initial setup if required."""
    print("First-time setup required...")

    try:
        import setup
        if setup.run_setup():
            print("\nSetup completed successfully!")
            return True
        else:
            print("\nSetup failed. Please check the errors above.")
            return False
    except ImportError:
        # Fallback: basic directory creation
        print("Setup module not found, creating basic directory structure...")
        return create_basic_directories()


def create_basic_directories():
    """Fallback directory creation if setup.py is not available."""
    base_dir = Path("src")
    directories = ['images_ingest', 'images_clean', 'images_originals', 'db', 'logs', 'src']

    try:
        for dirname in directories:
            (base_dir / dirname).mkdir(exist_ok=True)
            print(f"✓ Created {dirname}/")

        # Create basic README for ingest
        ingest_readme = base_dir / 'images_ingest' / 'README.txt'
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
    print("1. Place images in the 'images_ingest/' folder")
    print("2. Run this program and follow the interactive prompts")
    print("3. Collect cleaned images from the 'images_clean/' folder")
    print()


def main():
    """Main interactive interface with setup check."""

    # Check for required dependencies first
    if not check_dependencies():
        print("\nPlease install required packages and try again.")
        sys.exit(1)

    # Check if setup is required
    missing_dirs = check_setup_required()

    if missing_dirs:
        print(f"Missing directories: {', '.join(missing_dirs)}")

        if len(missing_dirs) >= 3:  # If multiple dirs missing, probably first run
            response = input("Run initial setup? (y/n) [y]: ").lower()
            if not response.startswith('n'):
                if not run_initial_setup():
                    print("Setup failed. Exiting.")
                    sys.exit(1)

                # Brief pause to let user read setup output
                input("\nPress Enter to continue to main interface...")
        else:
            # Just create missing directories
            print("Creating missing directories...")
            for dirname in missing_dirs:
                Path(dirname).mkdir(exist_ok=True)
                print(f"✓ Created {dirname}/")

    # Show welcome message
    show_welcome_message()

    # Initialize pipeline
    try:
        pipeline = SecurePipeline()
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
            for dirname in ['images_ingest', 'images_clean', 'images_originals', 'db', 'logs']:
                dir_path = pipeline.base_dir / dirname
                if dir_path.exists():
                    files = list(dir_path.glob('*'))
                    count = len([f for f in files if f.is_file()])
                    print(f"  {dirname}/  ({count} files)")
                else:
                    print(f"  {dirname}/  (missing)")

        elif choice == "4":
            # Run setup again
            print("\nRunning setup...")
            run_initial_setup()

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