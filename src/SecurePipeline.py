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

class SecurePipeline:
    """Main pipeline orchestrator."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.setup_directories()

        # Initialize components
        self.db = DatabaseManager(str(self.base_dir / "db" / "processing.db"))

        # Default configuration
        self.config = {
            'lsb_flip_probability': 0.15,
            'obfuscation_passes': 2,
            'add_noise': True,
            'output_format': 'JPEG',
            'jpeg_quality': 85,
            'operator_name': 'Anonymous'
        }

        self.processor = SecureImageProcessor(self.config)

    def setup_directories(self):
        """Create required directory structure."""
        for dirname in ['ingest', 'clean', 'originals', 'db', 'logs']:
            (self.base_dir / dirname).mkdir(exist_ok=True)

    def get_user_configuration(self):
        """Interactive configuration setup."""
        print("\n=== SECURE IMAGE PROCESSING PIPELINE ===")
        print("Configuration Setup\n")

        # Operator name
        operator = input("Enter operator name (for audit trail): ").strip()
        if operator:
            self.config['operator_name'] = operator

        # Security level
        print("\nSecurity Level:")
        print("1. Standard (15% LSB flip, 2 passes)")
        print("2. High (20% LSB flip, 3 passes)")
        print("3. Maximum (25% LSB flip, 3 passes + extra noise)")
        print("4. Custom")

        level = input("Choose security level (1-4) [1]: ").strip() or "1"

        if level == "2":
            self.config.update({
                'lsb_flip_probability': 0.20,
                'obfuscation_passes': 3
            })
        elif level == "3":
            self.config.update({
                'lsb_flip_probability': 0.25,
                'obfuscation_passes': 3,
                'add_noise': True
            })
        elif level == "4":
            # Custom configuration
            try:
                prob = float(input("LSB flip probability (0.05-0.30) [0.15]: ") or "0.15")
                self.config['lsb_flip_probability'] = max(0.05, min(0.30, prob))

                passes = int(input("Obfuscation passes (1-5) [2]: ") or "2")
                self.config['obfuscation_passes'] = max(1, min(5, passes))

                noise = input("Add noise disruption? (y/n) [y]: ").lower().startswith('y')
                self.config['add_noise'] = noise != False
            except ValueError:
                print("Invalid input, using defaults")

        # Output format
        print(f"\nOutput format:")
        print("1. JPEG (recommended - adds compression artifacts)")
        print("2. PNG (lossless)")

        format_choice = input("Choose format (1-2) [1]: ").strip() or "1"
        if format_choice == "2":
            self.config['output_format'] = 'PNG'

        # JPEG quality if needed
        if self.config['output_format'] == 'JPEG':
            try:
                quality = int(input("JPEG quality (70-95) [85]: ") or "85")
                self.config['jpeg_quality'] = max(70, min(95, quality))
            except ValueError:
                pass

        print(f"\n=== CONFIGURATION SUMMARY ===")
        print(f"Operator: {self.config['operator_name']}")
        print(f"LSB flip probability: {self.config['lsb_flip_probability']}")
        print(f"Obfuscation passes: {self.config['obfuscation_passes']}")
        print(f"Add noise: {self.config['add_noise']}")
        print(f"Output format: {self.config['output_format']}")
        if self.config['output_format'] == 'JPEG':
            print(f"JPEG quality: {self.config['jpeg_quality']}")

        confirm = input("\nProceed with this configuration? (y/n) [y]: ").lower()
        if confirm.startswith('n'):
            print("Configuration cancelled.")
            return False

        # Update processor with new config
        self.processor = SecureImageProcessor(self.config)
        return True

    def scan_ingest_folder(self) -> List[Path]:
        """Scan ingest folder for image files."""
        supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        image_files = []

        ingest_dir = self.base_dir / 'ingest'
        for file_path in ingest_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                image_files.append(file_path)

        return sorted(image_files)

    def process_single_image(self, input_path: Path, run_id: int) -> bool:
        """Process a single image through the secure pipeline."""
        try:
            print(f"Processing: {input_path.name}")

            # Generate timestamped filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            stem = input_path.stem

            # Step 1: Load and analyze original
            with Image.open(input_path) as original_img:
                # Extract metadata for preservation
                preserved_metadata = self.processor.extract_all_metadata(original_img)

                # Get image info
                img_info = {
                    'width': original_img.width,
                    'height': original_img.height,
                    'format': original_img.format,
                    'mode': original_img.mode,
                    'file_size': input_path.stat().st_size
                }

                # Calculate original hash
                original_hash = self.processor.calculate_file_hash(str(input_path))

                # Step 2: Create preserved copy in originals/
                original_filename = f"{timestamp}__{input_path.name}"
                original_path = self.base_dir / 'originals' / original_filename
                shutil.copy2(input_path, original_path)

                # Record original file
                original_file_id = self.db.record_file(
                    run_id, 'original', input_path.name,
                    str(original_path), original_hash, img_info
                )

                # Record preserved metadata
                self.db.record_preserved_metadata(original_file_id, preserved_metadata)

                # Record preservation action
                self.db.record_action(run_id, original_file_id, 'preserve_original', {
                    'original_path': str(input_path),
                    'preserved_path': str(original_path),
                    'hash_sha256': original_hash
                })

                # Step 3: Apply secure obfuscation
                clean_img, obfuscation_log = self.processor.strip_metadata_and_obfuscate(original_img)

                # Step 4: Save cleaned image
                clean_filename = f"{timestamp}__{stem}_clean.jpg" if self.config[
                                                                         'output_format'] == 'JPEG' else f"{timestamp}__{stem}_clean.png"
                clean_path = self.base_dir / 'clean' / clean_filename

                save_params = {}
                if self.config['output_format'] == 'JPEG':
                    save_params = {
                        'quality': self.config['jpeg_quality'],
                        'optimize': True,
                        'progressive': True
                    }
                elif self.config['output_format'] == 'PNG':
                    save_params = {'optimize': True}

                clean_img.save(clean_path, self.config['output_format'], **save_params)

                # Calculate cleaned file hash and info
                clean_hash = self.processor.calculate_file_hash(str(clean_path))
                clean_info = {
                    'width': clean_img.width,
                    'height': clean_img.height,
                    'format': self.config['output_format'],
                    'mode': clean_img.mode,
                    'file_size': clean_path.stat().st_size
                }

                # Record cleaned file
                cleaned_file_id = self.db.record_file(
                    run_id, 'cleaned', clean_filename,
                    str(clean_path), clean_hash, clean_info
                )

                # Record obfuscation details
                obfuscation_log['lsb_flip_probability'] = self.config['lsb_flip_probability']
                self.db.record_obfuscation_summary(
                    cleaned_file_id, original_file_id, obfuscation_log,
                    original_img.format, self.config['output_format']
                )

                # Record processing action
                self.db.record_action(run_id, cleaned_file_id, 'secure_obfuscation', {
                    'input_hash': original_hash,
                    'output_hash': clean_hash,
                    'obfuscation_details': obfuscation_log,
                    'format_change': original_img.format != self.config['output_format']
                })

                # Step 5: Remove original from ingest
                input_path.unlink()
                self.db.record_action(run_id, original_file_id, 'remove_from_ingest', {
                    'ingest_path': str(input_path)
                })

                print(f"  ✓ Original preserved: {original_path.name}")
                print(f"  ✓ Cleaned version: {clean_path.name}")
                print(
                    f"  ✓ Metadata stripped: {bool(preserved_metadata['exif_data'] or preserved_metadata['other_info'])}")
                print(f"  ✓ LSB randomization: {obfuscation_log['passes_applied']} passes")

                return True

        except Exception as e:
            print(f"  ✗ Error processing {input_path.name}: {str(e)}")
            # Record failure
            self.db.record_action(run_id, 0, 'processing_error', {
                'file': str(input_path),
                'error': str(e)
            })
            return False

    def run_processing_batch(self):
        """Run batch processing on all images in ingest folder."""
        image_files = self.scan_ingest_folder()

        if not image_files:
            print("No images found in ingest folder.")
            return

        print(f"\nFound {len(image_files)} image(s) to process:")
        for img_file in image_files:
            print(f"  - {img_file.name}")

        proceed = input(f"\nProcess all {len(image_files)} images? (y/n) [y]: ").lower()
        if proceed.startswith('n'):
            print("Processing cancelled.")
            return

        # Start processing run
        run_id = self.db.start_run(self.config['operator_name'], self.config)

        print(f"\n=== PROCESSING BATCH (Run ID: {run_id}) ===")

        stats = {'total': len(image_files), 'successful': 0, 'failed': 0}

        for img_file in image_files:
            if self.process_single_image(img_file, run_id):
                stats['successful'] += 1
            else:
                stats['failed'] += 1
            print()  # Empty line between files

        # Finish run
        self.db.finish_run(run_id, stats)

        print("=== PROCESSING COMPLETE ===")
        print(f"Total files: {stats['total']}")
        print(f"Successfully processed: {stats['successful']}")
        print(f"Failed: {stats['failed']}")

        if stats['successful'] > 0:
            print(f"\nCleaned images available in: {self.base_dir / 'clean'}")
            print(f"Originals preserved in: {self.base_dir / 'originals'}")
            print(f"Audit trail in database: {self.base_dir / 'db' / 'processing.db'}")

    def show_database_summary(self):
        """Display summary of database contents."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()

                # Get run statistics
                cursor.execute("""
                    SELECT COUNT(*) as total_runs,
                           SUM(total_files) as total_files,
                           SUM(successful_files) as successful_files
                    FROM runs
                """)
                run_stats = cursor.fetchone()

                # Get recent runs
                cursor.execute("""
                    SELECT run_id, started_at_utc, operator_name, total_files, successful_files
                    FROM runs 
                    ORDER BY run_id DESC 
                    LIMIT 5
                """)
                recent_runs = cursor.fetchall()

                print("\n=== DATABASE SUMMARY ===")
                print(f"Total runs: {run_stats[0] or 0}")
                print(f"Total files processed: {run_stats[1] or 0}")
                print(f"Successfully processed: {run_stats[2] or 0}")

                if recent_runs:
                    print(f"\nRecent runs:")
                    for run in recent_runs:
                        print(f"  Run {run[0]}: {run[1][:19]} - {run[2]} - {run[4]}/{run[3]} files")

        except Exception as e:
            print(f"Error reading database: {e}")