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
import secrets

# Image processing imports
from PIL import Image, ImageFilter, ImageEnhance
from PIL import ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
import numpy as np
import random


class SecureImageProcessor:
    """Core image processing with LSB obfuscation and metadata removal."""

    def __init__(self, config: Dict):
        self.config = config
        self.secure_random = random.SystemRandom()

    @staticmethod
    def _serialize_metadata_value(value) -> str:
        """Convert metadata values to a JSON-serializable representation."""
        if isinstance(value, (bytes, bytearray)):
            return f"<{len(value)} bytes>"
        return str(value)

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
                    if tag == 'GPSInfo' and isinstance(value, dict):
                        gps_data = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[gps_tag] = self._serialize_metadata_value(gps_value)
                        metadata['exif_gps'] = gps_data
                    else:
                        metadata['exif_data'][str(tag)] = self._serialize_metadata_value(value)

                if hasattr(exif, "get_ifd"):
                    ifd_map = getattr(ExifTags, "IFD", None)
                    if ifd_map:
                        if hasattr(ifd_map, "items"):
                            ifd_iterable = ifd_map.items()
                        elif hasattr(ifd_map, "__members__"):
                            ifd_iterable = ifd_map.__members__.items()
                        else:
                            ifd_iterable = []

                        for ifd_name, ifd_value in ifd_iterable:
                            if hasattr(ifd_value, "value"):
                                ifd_id = ifd_value.value
                            else:
                                ifd_id = ifd_value

                            try:
                                ifd = exif.get_ifd(ifd_id)
                            except (KeyError, AttributeError, TypeError):
                                continue

                            if not ifd:
                                continue

                            formatted_ifd = {}
                            for nested_tag_id, nested_value in ifd.items():
                                tag_name = TAGS.get(nested_tag_id, f"Unknown_{nested_tag_id}")
                                formatted_ifd[tag_name] = self._serialize_metadata_value(nested_value)

                            if formatted_ifd:
                                metadata['exif_data'][f"{ifd_name}_IFD"] = formatted_ifd

                maker_note_tag = None
                tags_v2 = getattr(ExifTags, "TAGS_V2", None)
                if isinstance(tags_v2, dict):
                    maker_note_tag = tags_v2.get('MakerNote')

                if maker_note_tag is None:
                    for tag_id, tag_name in TAGS.items():
                        if tag_name == 'MakerNote':
                            maker_note_tag = tag_id
                            break

                if maker_note_tag is not None:
                    maker_note_value = exif.get(maker_note_tag)
                    if maker_note_value:
                        metadata['exif_data']['MakerNote'] = self._serialize_metadata_value(maker_note_value)
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
        if img_array.size == 0:
            return img_array

        prob = max(0.0, min(1.0, float(flip_probability)))
        if prob <= 0.0:
            return img_array.astype(np.uint8)
        if prob >= 1.0:
            return (img_array ^ 1).astype(np.uint8)

        height, width, channels = img_array.shape
        threshold = int(prob * 256)
        random_bytes = secrets.token_bytes(img_array.size)
        random_values = np.frombuffer(random_bytes, dtype=np.uint8).reshape(height, width, channels)
        flip_mask = random_values < threshold

        result = np.where(flip_mask, img_array ^ 1, img_array)
        return result.astype(np.uint8)

    def _add_subtle_noise(self, img_array: np.ndarray, noise_level: float) -> np.ndarray:
        """Add subtle noise to disrupt patterns."""
        if img_array.size == 0 or noise_level <= 0:
            return img_array.astype(np.uint8)

        noise_bytes = secrets.token_bytes(img_array.size)
        noise_array = np.frombuffer(noise_bytes, dtype=np.uint8).reshape(img_array.shape)
        noise = (noise_array.astype(np.float32) - 127.5) * (float(noise_level) / 127.5)
        noisy = img_array.astype(np.float32) + noise
        return np.clip(noisy, 0, 255).astype(np.uint8)

