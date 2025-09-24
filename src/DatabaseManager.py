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

class DatabaseManager:
    """Manages SQLite database for audit trail."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Create database tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")

            # Processing runs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at_utc TEXT NOT NULL,
                    finished_at_utc TEXT,
                    operator_name TEXT,
                    total_files INTEGER DEFAULT 0,
                    successful_files INTEGER DEFAULT 0,
                    failed_files INTEGER DEFAULT 0,
                    configuration_json TEXT
                )
            """)

            # Files table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER REFERENCES runs(run_id),
                    file_type TEXT CHECK (file_type IN ('original','cleaned')) NOT NULL,
                    original_filename TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    file_hash_sha256 TEXT NOT NULL,
                    file_size_bytes INTEGER,
                    image_width INTEGER,
                    image_height INTEGER,
                    image_format TEXT,
                    image_mode TEXT,
                    created_at_utc TEXT NOT NULL
                )
            """)

            # File relationships
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_relationships (
                    original_file_id INTEGER NOT NULL REFERENCES files(file_id),
                    cleaned_file_id INTEGER NOT NULL REFERENCES files(file_id),
                    PRIMARY KEY (original_file_id, cleaned_file_id)
                )
            """)

            # Preserved metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preserved_metadata (
                    file_id INTEGER PRIMARY KEY REFERENCES files(file_id),
                    exif_data_json TEXT,
                    exif_gps_json TEXT,
                    icc_profile_size INTEGER,
                    other_metadata_json TEXT,
                    had_transparency BOOLEAN,
                    original_mode TEXT
                )
            """)

            # Processing actions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_actions (
                    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER REFERENCES runs(run_id),
                    file_id INTEGER REFERENCES files(file_id),
                    action_type TEXT NOT NULL,
                    action_details_json TEXT,
                    timestamp_utc TEXT NOT NULL
                )
            """)

            # Obfuscation summary
            conn.execute("""
                CREATE TABLE IF NOT EXISTS obfuscation_summary (
                    cleaned_file_id INTEGER PRIMARY KEY REFERENCES files(file_id),
                    metadata_stripped BOOLEAN DEFAULT TRUE,
                    lsb_randomization_applied BOOLEAN DEFAULT TRUE,
                    transparency_removed BOOLEAN DEFAULT FALSE,
                    noise_added BOOLEAN DEFAULT FALSE,
                    obfuscation_passes INTEGER DEFAULT 1,
                    lsb_flip_probability REAL,
                    format_changed BOOLEAN DEFAULT FALSE,
                    original_format TEXT,
                    cleaned_format TEXT
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash_sha256)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_type ON files(file_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_run ON files(run_id)")

            conn.commit()

    def start_run(self, operator_name: str, config: Dict) -> int:
        """Start a new processing run."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO runs (started_at_utc, operator_name, configuration_json)
                VALUES (?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                operator_name,
                json.dumps(config, indent=2)
            ))
            conn.commit()
            return cursor.lastrowid

    def finish_run(self, run_id: int, stats: Dict):
        """Complete a processing run with statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE runs SET 
                    finished_at_utc = ?,
                    total_files = ?,
                    successful_files = ?,
                    failed_files = ?
                WHERE run_id = ?
            """, (
                datetime.now(timezone.utc).isoformat(),
                stats['total'],
                stats['successful'],
                stats['failed'],
                run_id
            ))
            conn.commit()

    def record_file(self, run_id: int, file_type: str, filename: str,
                    stored_path: str, file_hash: str, metadata: Dict) -> int:
        """Record a file in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO files (
                    run_id, file_type, original_filename, stored_path,
                    file_hash_sha256, file_size_bytes, image_width, image_height,
                    image_format, image_mode, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, file_type, filename, stored_path, file_hash,
                metadata.get('file_size', 0),
                metadata.get('width', 0),
                metadata.get('height', 0),
                metadata.get('format', ''),
                metadata.get('mode', ''),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
            return cursor.lastrowid

    def record_preserved_metadata(self, file_id: int, metadata: Dict):
        """Record preserved metadata for an original file."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO preserved_metadata (
                    file_id, exif_data_json, exif_gps_json, icc_profile_size,
                    other_metadata_json, had_transparency, original_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                json.dumps(metadata.get('exif_data', {})),
                json.dumps(metadata.get('exif_gps', {})),
                metadata.get('icc_profile', 0),
                json.dumps(metadata.get('other_info', {})),
                metadata.get('has_transparency', False),
                metadata.get('original_mode', '')
            ))
            conn.commit()

    def record_obfuscation_summary(self, cleaned_file_id: int, original_file_id: int,
                                   obfuscation_log: Dict, original_format: str, cleaned_format: str):
        """Record obfuscation summary."""
        with sqlite3.connect(self.db_path) as conn:
            # Link files
            conn.execute("""
                INSERT OR IGNORE INTO file_relationships (original_file_id, cleaned_file_id)
                VALUES (?, ?)
            """, (original_file_id, cleaned_file_id))

            # Record obfuscation details
            conn.execute("""
                INSERT INTO obfuscation_summary (
                    cleaned_file_id, metadata_stripped, lsb_randomization_applied,
                    transparency_removed, noise_added, obfuscation_passes,
                    lsb_flip_probability, format_changed, original_format, cleaned_format
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cleaned_file_id,
                obfuscation_log.get('metadata_stripped', True),
                obfuscation_log.get('lsb_randomization_applied', True),
                obfuscation_log.get('transparency_removed', False),
                obfuscation_log.get('noise_added', False),
                obfuscation_log.get('passes_applied', 1),
                obfuscation_log.get('lsb_flip_probability', 0.15),
                original_format.upper() != cleaned_format.upper(),
                original_format,
                cleaned_format
            ))
            conn.commit()

    def record_action(self, run_id: int, file_id: int, action_type: str, details: Dict):
        """Record a processing action."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO processing_actions (run_id, file_id, action_type, action_details_json, timestamp_utc)
                VALUES (?, ?, ?, ?, ?)
            """, (
                run_id, file_id, action_type,
                json.dumps(details),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()