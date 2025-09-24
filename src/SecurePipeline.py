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
        provided_base = Path(base_dir).expanduser().resolve()
        base_dir_override = os.getenv("PIPELINE_BASE_DIR")
        if base_dir_override:
            override_candidate = Path(base_dir_override).expanduser()
            if override_candidate.is_absolute():
                resolved_base = override_candidate.resolve()
            else:
                resolved_base = (provided_base / override_candidate).resolve()
        else:
            resolved_base = provided_base
        self.base_dir = resolved_base

        self.directory_names = {
            'ingest': os.getenv("PIPELINE_INGEST_DIR", "ingest"),
            'clean': os.getenv("PIPELINE_CLEAN_DIR", "clean"),
            'originals': os.getenv("PIPELINE_ORIGINALS_DIR", "originals"),
            'db': os.getenv("PIPELINE_DB_DIR", "db"),
            'logs': os.getenv("PIPELINE_LOG_DIR", "logs"),
        }
        self.directories = {
            key: self.base_dir / Path(name)
            for key, name in self.directory_names.items()
        }

        self.db_filename = os.getenv("PIPELINE_DB_FILENAME", "processing.db")
        self.db_path = self.directories['db'] / self.db_filename

        self.setup_directories()

        # Initialize components
        self.db = DatabaseManager(str(self.db_path))

        self.default_security_level = self._env_int("PIPELINE_DEFAULT_SECURITY_LEVEL", 1, 1, 4)

        # Default configuration
        self.config = {
            'lsb_flip_probability': self._env_float("PIPELINE_LSB_FLIP_PROBABILITY", 0.15, 0.05, 0.30),
            'obfuscation_passes': self._env_int("PIPELINE_OBFUSCATION_PASSES", 2, 1, 5),
            'add_noise': self._env_bool("PIPELINE_ADD_NOISE", True),
            'output_format': self._validate_output_format(os.getenv("PIPELINE_OUTPUT_FORMAT", "JPEG")),
            'jpeg_quality': self._env_int("PIPELINE_JPEG_QUALITY", 85, 70, 95),
            'operator_name': os.getenv("PIPELINE_DEFAULT_OPERATOR", "Anonymous")
        }

        self.processor = SecureImageProcessor(self.config)

    @staticmethod
    def _env_float(
        var_name: str,
        default: float,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
    ) -> float:
        value = os.getenv(var_name)
        if value is None:
            return default
        try:
            parsed = float(value)
        except ValueError:
            return default

        if minimum is not None:
            parsed = max(minimum, parsed)
        if maximum is not None:
            parsed = min(maximum, parsed)
        return parsed

    @staticmethod
    def _env_int(
        var_name: str,
        default: int,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
    ) -> int:
        value = os.getenv(var_name)
        if value is None:
            return default
        try:
            parsed = int(value)
        except ValueError:
            return default

        if minimum is not None:
            parsed = max(minimum, parsed)
        if maximum is not None:
            parsed = min(maximum, parsed)
        return parsed

    @staticmethod
    def _env_bool(var_name: str, default: bool) -> bool:
        value = os.getenv(var_name)
        if value is None:
            return default

        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return default

    @staticmethod
    def _validate_output_format(value: str) -> str:
        normalized = (value or "").strip().upper()
        if normalized not in {"JPEG", "PNG"}:
            return "JPEG"
        return normalized

    def setup_directories(self):
        """Create required directory structure."""
        for path in self.directories.values():
            path.mkdir(parents=True, exist_ok=True)

    def get_user_configuration(self):
        """Interactive configuration setup."""
        print("\n=== SECURE IMAGE PROCESSING PIPELINE ===")
        print("Configuration Setup\n")

        # Operator name
        operator_prompt = f"Enter operator name (for audit trail) [{self.config['operator_name']}]: "
        operator = input(operator_prompt).strip()
        if operator:
            self.config['operator_name'] = operator

        # Security level
        print("\nSecurity Level:")
        print("1. Standard (15% LSB flip, 2 passes)")
        print("2. High (20% LSB flip, 3 passes)")
        print("3. Maximum (25% LSB flip, 3 passes + extra noise)")
        print("4. Custom")

        default_level = str(self.default_security_level)
        level = input(f"Choose security level (1-4) [{default_level}]: ").strip() or default_level

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
                prob_default = f"{self.config['lsb_flip_probability']:.2f}"
                prob_input = input(
                    f"LSB flip probability (0.05-0.30) [{prob_default}]: "
                ).strip()
                if prob_input:
                    prob = float(prob_input)
                    self.config['lsb_flip_probability'] = max(0.05, min(0.30, prob))

                passes_input = input(
                    f"Obfuscation passes (1-5) [{self.config['obfuscation_passes']}]: "
                ).strip()
                if passes_input:
                    passes = int(passes_input)
                    self.config['obfuscation_passes'] = max(1, min(5, passes))

                noise_default = 'y' if self.config['add_noise'] else 'n'
                noise_input = input(
                    f"Add noise disruption? (y/n) [{noise_default}]: "
                ).strip().lower()
                if noise_input:
                    self.config['add_noise'] = not noise_input.startswith('n')
            except ValueError:
                print("Invalid input, using defaults")

        # Output format
        print(f"\nOutput format:")
        print("1. JPEG (recommended - adds compression artifacts)")
        print("2. PNG (lossless)")

        format_default = "1" if self.config['output_format'] == 'JPEG' else "2"
        format_choice = input(f"Choose format (1-2) [{format_default}]: ").strip() or format_default
        if format_choice == "2":
            self.config['output_format'] = 'PNG'
        
        # JPEG quality if needed
        if self.config['output_format'] == 'JPEG':
            try:
                quality_input = input(
                    f"JPEG quality (70-95) [{self.config['jpeg_quality']}]: "
                ).strip()
                if quality_input:
                    quality = int(quality_input)
                else:
                    quality = self.config['jpeg_quality']
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

        ingest_dir = self.directories['ingest']
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
                original_path = self.directories['originals'] / original_filename
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
                clean_filename = (
                    f"{timestamp}__{stem}_clean.jpg"
                    if self.config['output_format'] == 'JPEG'
                    else f"{timestamp}__{stem}_clean.png"
                )
                clean_path = self.directories['clean'] / clean_filename

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
            print(f"\nCleaned images available in: {self.directories['clean']}")
            print(f"Originals preserved in: {self.directories['originals']}")
            print(f"Audit trail in database: {self.db_path}")

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