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


class SecureImageProcessor:
    """Core image processing with LSB obfuscation and metadata removal."""

    def __init__(self, config: Dict):
        self.config = config
        self.secure_random = random.SystemRandom()

    def extract_all_metadata(self, img: Image.Image) -> Dict:
        """Extract comprehensive metadata for preservation."""
        metadata = {
            'exif_data': {},
            'exif_gps': {},
            'icc_profile': None,
            'other_info': {},
            'has_transparency': False,
            'original_mode': img.mode
        }

        # Extract EXIF
        try:
            exif = img.getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    # Handle GPS data separately
                    if tag == 'GPSInfo':
                        gps_data = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[gps_tag] = str(gps_value)
                        metadata['exif_gps'] = gps_data
                    else:
                        metadata['exif_data'][tag] = str(value)
        except Exception as e:
            metadata['exif_extraction_error'] = str(e)

        # Extract other PIL info
        for key, value in img.info.items():
            if key not in ['exif']:
                if key == 'icc_profile':
                    metadata['icc_profile'] = len(value) if value else 0
                else:
                    metadata['other_info'][key] = str(value)

        # Check transparency
        metadata['has_transparency'] = img.mode in ('RGBA', 'LA') or 'transparency' in img.info

        return metadata

    def calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def strip_metadata_and_obfuscate(self, img: Image.Image) -> Tuple[Image.Image, Dict]:
        """Apply secure obfuscation while preserving evidence of what was removed."""
        obfuscation_log = {
            'metadata_stripped': True,
            'lsb_randomization_applied': True,
            'transparency_removed': False,
            'format_normalized': True,
            'noise_added': False,
            'passes_applied': 1
        }

        # Convert to RGB and handle transparency
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:  # LA
                rgb_img = img.convert('RGB')
                background.paste(rgb_img)
            clean_img = background
            obfuscation_log['transparency_removed'] = True
        elif img.mode == 'P':
            clean_img = img.convert('RGB')
        else:
            clean_img = img.convert('RGB')

        # Apply LSB randomization
        img_array = np.array(clean_img)
        lsb_prob = self.config.get('lsb_flip_probability', 0.15)

        # Multi-pass LSB randomization
        passes = self.config.get('obfuscation_passes', 2)
        for pass_num in range(passes):
            img_array = self._randomize_lsb_bits(img_array, lsb_prob)

            # Add subtle noise on some passes
            if self.config.get('add_noise', True) and pass_num == 0:
                img_array = self._add_subtle_noise(img_array, 0.4)
                obfuscation_log['noise_added'] = True

        obfuscation_log['passes_applied'] = passes

        return Image.fromarray(img_array), obfuscation_log

    def _randomize_lsb_bits(self, img_array: np.ndarray, flip_probability: float) -> np.ndarray:
        """Randomly flip least significant bits."""
        height, width, channels = img_array.shape

        # Generate random mask
        flip_mask = self.secure_random.choices(
            [0, 1],
            weights=[1 - flip_probability, flip_probability],
            k=height * width * channels
        )
        flip_mask = np.array(flip_mask).reshape(height, width, channels)

        # Apply LSB flipping
        lsb_mask = np.ones_like(img_array, dtype=np.uint8)
        result = np.where(flip_mask, img_array ^ lsb_mask, img_array)

        return result.astype(np.uint8)

    def _add_subtle_noise(self, img_array: np.ndarray, noise_level: float) -> np.ndarray:
        """Add subtle noise to disrupt patterns."""
        noise = np.random.normal(0, noise_level, img_array.shape)
        noisy = img_array.astype(np.float32) + noise
        return np.clip(noisy, 0, 255).astype(np.uint8)