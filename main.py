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



def main():
    """Main interactive interface."""
    print("Secure Image Processing Pipeline")
    print("Human Rights Documentation Tool")
    print("=" * 50)

    # Initialize pipeline
    pipeline = SecurePipeline()

    while True:
        print(f"\nWorking directory: {pipeline.base_dir.absolute()}")
        print("\nOptions:")
        print("1. Configure and process images")
        print("2. View database summary")
        print("3. Show directory structure")
        print("4. Exit")

        choice = input("\nSelect option (1-4): ").strip()

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
            for dirname in ['ingest', 'clean', 'originals', 'db']:
                dir_path = pipeline.base_dir / dirname
                count = len(list(dir_path.glob('*'))) if dir_path.exists() else 0
                print(f"  {dirname}/  ({count} files)")

        elif choice == "4":
            print("\nExiting pipeline. Stay safe.")
            break

        else:
            print("Invalid option. Please choose 1-4.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Please report this issue if it persists.")