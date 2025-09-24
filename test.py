#!/usr/bin/env python3
"""
Steganography Test Script for Secure Image Processing Pipeline

This script tests the effectiveness of the image scrubbing pipeline by:
1. Creating a test image or using an existing one
2. Embedding a steganographic message using LSB technique
3. Verifying the message can be extracted
4. Running the image through the scrubbing pipeline
5. Verifying the message is no longer extractable

Usage: python test_steganography.py [test_image.png]
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from PIL import Image
import hashlib

# Import the pipeline components
from src.SecureImageProcessor import SecureImageProcessor
from src.DatabaseManager import DatabaseManager


class LSBSteganography:
    """Simple LSB steganography implementation for testing."""

    DELIMITER = "###END_OF_MESSAGE###"

    @staticmethod
    def text_to_binary(text: str) -> str:
        """Convert text to binary representation."""
        return ''.join(format(ord(char), '08b') for char in text)

    @staticmethod
    def binary_to_text(binary: str) -> str:
        """Convert binary representation back to text."""
        chars = []
        for i in range(0, len(binary), 8):
            byte = binary[i:i + 8]
            if len(byte) == 8:
                chars.append(chr(int(byte, 2)))
        return ''.join(chars)

    @classmethod
    def embed_message(cls, image_path: str, message: str, output_path: str) -> bool:
        """Embed a message into an image using LSB steganography."""
        try:
            # Load image
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Convert to numpy array
            img_array = np.array(img)

            # Prepare message with delimiter
            full_message = message + cls.DELIMITER
            binary_message = cls.text_to_binary(full_message)

            # Check if image can hold the message
            total_pixels = img_array.shape[0] * img_array.shape[1]
            max_bits = total_pixels * 3  # 3 channels (RGB)

            if len(binary_message) > max_bits:
                print(f"ERROR: Message too long ({len(binary_message)} bits) for image ({max_bits} bits available)")
                return False

            print(f"Embedding {len(binary_message)} bits into image...")

            # Embed message
            flat_img = img_array.flatten()
            bit_index = 0

            for i in range(len(flat_img)):
                if bit_index < len(binary_message):
                    # Clear LSB and set to message bit
                    flat_img[i] = (flat_img[i] & 0xFE) | int(binary_message[bit_index])
                    bit_index += 1
                else:
                    break

            # Reshape and save
            modified_img = flat_img.reshape(img_array.shape)
            result_img = Image.fromarray(modified_img.astype(np.uint8))
            result_img.save(output_path)

            print(f"Message embedded successfully in {output_path}")
            return True

        except Exception as e:
            print(f"ERROR embedding message: {e}")
            return False

    @classmethod
    def extract_message(cls, image_path: str) -> Optional[str]:
        """Extract a message from an image using LSB steganography."""
        try:
            # Load image
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Convert to numpy array
            img_array = np.array(img)
            flat_img = img_array.flatten()

            # Extract LSBs
            binary_message = ''
            for pixel_value in flat_img:
                binary_message += str(pixel_value & 1)

            # Convert to text and look for delimiter
            try:
                text_message = cls.binary_to_text(binary_message)
                if cls.DELIMITER in text_message:
                    extracted = text_message.split(cls.DELIMITER)[0]
                    return extracted
                else:
                    return None
            except:
                return None

        except Exception as e:
            print(f"ERROR extracting message: {e}")
            return None


def create_test_image(width: int = 256, height: int = 256) -> str:
    """Create a simple test image if none provided."""
    # Create a gradient image for testing
    img_array = np.zeros((height, width, 3), dtype=np.uint8)

    for i in range(height):
        for j in range(width):
            img_array[i, j] = [
                int(255 * i / height),  # Red gradient
                int(255 * j / width),  # Green gradient
                128  # Blue constant
            ]

    img = Image.fromarray(img_array)
    test_path = "test_gradient.png"
    img.save(test_path)
    print(f"Created test image: {test_path}")
    return test_path


def calculate_image_hash(image_path: str) -> str:
    """Calculate SHA-256 hash of image file."""
    sha256_hash = hashlib.sha256()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def run_scrubbing_pipeline(input_image: str, temp_dir: Path) -> Optional[str]:
    """Run the image through the scrubbing pipeline."""
    print("\n" + "=" * 60)
    print("RUNNING SCRUBBING PIPELINE")
    print("=" * 60)

    try:
        # Set up temporary directories
        ingest_dir = temp_dir / "ingest"
        clean_dir = temp_dir / "clean"
        originals_dir = temp_dir / "originals"
        db_dir = temp_dir / "db"

        for dir_path in [ingest_dir, clean_dir, originals_dir, db_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Copy image to ingest
        input_path = Path(input_image)
        ingest_path = ingest_dir / input_path.name
        shutil.copy2(input_image, ingest_path)

        # Initialize database
        db_path = db_dir / "test_processing.db"
        db = DatabaseManager(str(db_path))

        # Configure processor for aggressive scrubbing
        config = {
            'lsb_flip_probability': 0.25,  # High probability
            'obfuscation_passes': 3,  # Multiple passes
            'add_noise': True,  # Add noise
            'output_format': 'JPEG',  # JPEG compression
            'jpeg_quality': 75  # Moderate compression
        }

        processor = SecureImageProcessor(config)

        # Start processing run
        run_id = db.start_run("test_operator", config)

        print(f"Processing {input_path.name} with aggressive settings...")
        print(f"- LSB flip probability: {config['lsb_flip_probability']}")
        print(f"- Obfuscation passes: {config['obfuscation_passes']}")
        print(f"- Add noise: {config['add_noise']}")

        # Process the image
        with Image.open(ingest_path) as original_img:
            # Extract metadata
            preserved_metadata = processor.extract_all_metadata(original_img)

            # Apply obfuscation
            clean_img, obfuscation_log = processor.strip_metadata_and_obfuscate(original_img)

            # Save cleaned image
            clean_filename = f"cleaned_{input_path.stem}.jpg"
            clean_path = clean_dir / clean_filename

            clean_img.save(clean_path, 'JPEG', quality=config['jpeg_quality'], optimize=True)

            print(f"✓ Processed image saved as: {clean_path}")
            print(f"✓ LSB passes applied: {obfuscation_log['passes_applied']}")
            print(f"✓ Noise added: {obfuscation_log['noise_added']}")

            return str(clean_path)

    except Exception as e:
        print(f"ERROR in scrubbing pipeline: {e}")
        return None


def main():
    """Main test function."""
    print("STEGANOGRAPHY SCRUBBING TEST")
    print("=" * 60)

    # Get test image
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        if not Path(test_image).exists():
            print(f"ERROR: Image file {test_image} not found")
            return False
    else:
        print("No image provided, creating test image...")
        test_image = create_test_image()

    print(f"Using test image: {test_image}")

    # Test message
    secret_message = "This is a secret message embedded using LSB steganography. If you can read this after scrubbing, the pipeline failed!"

    # Create temporary directory for test files
    with tempfile.TemporaryDirectory(prefix="steg_test_") as temp_dir:
        temp_path = Path(temp_dir)

        print(f"\nWorking in temporary directory: {temp_dir}")

        # STEP 1: Test original image (should have no message)
        print(f"\n{'=' * 60}")
        print("STEP 1: Testing original image for existing steganography")
        print("=" * 60)

        original_hash = calculate_image_hash(test_image)
        print(f"Original image hash: {original_hash[:16]}...")

        extracted = LSBSteganography.extract_message(test_image)
        if extracted:
            print(f"⚠️  WARNING: Original image already contains a message: '{extracted[:50]}...'")
        else:
            print("✓ Original image is clean (no steganographic message detected)")

        # STEP 2: Embed steganographic message
        print(f"\n{'=' * 60}")
        print("STEP 2: Embedding steganographic message")
        print("=" * 60)

        steg_image = temp_path / f"steg_{Path(test_image).name}"

        print(f"Secret message ({len(secret_message)} chars): '{secret_message[:50]}...'")

        if not LSBSteganography.embed_message(test_image, secret_message, str(steg_image)):
            print("ERROR: Failed to embed message")
            return False

        steg_hash = calculate_image_hash(str(steg_image))
        print(f"Steganographic image hash: {steg_hash[:16]}...")
        print(f"Hash changed: {original_hash != steg_hash}")

        # STEP 3: Verify message can be extracted
        print(f"\n{'=' * 60}")
        print("STEP 3: Verifying message extraction")
        print("=" * 60)

        extracted_before = LSBSteganography.extract_message(str(steg_image))
        if extracted_before == secret_message:
            print("✓ Message successfully extracted from steganographic image")
            print(f"  Extracted: '{extracted_before[:50]}...'")
        else:
            print("ERROR: Message extraction failed or incorrect")
            print(f"  Expected: '{secret_message[:50]}...'")
            print(f"  Got: '{extracted_before[:50] if extracted_before else 'None'}...'")
            return False

        # STEP 4: Run scrubbing pipeline
        print(f"\n{'=' * 60}")
        print("STEP 4: Running scrubbing pipeline")
        print("=" * 60)

        scrubbed_image = run_scrubbing_pipeline(str(steg_image), temp_path)
        if not scrubbed_image:
            print("ERROR: Scrubbing pipeline failed")
            return False

        scrubbed_hash = calculate_image_hash(scrubbed_image)
        print(f"Scrubbed image hash: {scrubbed_hash[:16]}...")

        # STEP 5: Test scrubbed image
        print(f"\n{'=' * 60}")
        print("STEP 5: Testing scrubbed image")
        print("=" * 60)

        extracted_after = LSBSteganography.extract_message(scrubbed_image)

        if extracted_after is None:
            print("✅ SUCCESS: No steganographic message detected in scrubbed image")
            print("✅ Pipeline successfully removed steganographic content")
        elif extracted_after == secret_message:
            print("❌ FAILURE: Original message still extractable from scrubbed image")
            print(f"   Message: '{extracted_after[:50]}...'")
            print("❌ Pipeline failed to remove steganographic content")
            return False
        else:
            print("⚠️  PARTIAL SUCCESS: Different message extracted (content disrupted)")
            print(f"   Original: '{secret_message[:50]}...'")
            print(f"   Extracted: '{extracted_after[:50]}...'")
            print("✅ Pipeline disrupted steganographic content (acceptable result)")

        # STEP 6: Summary
        print(f"\n{'=' * 60}")
        print("TEST SUMMARY")
        print("=" * 60)

        print(f"Original image: {test_image}")
        print(f"Original hash: {original_hash[:16]}...")
        print(f"Steg hash: {steg_hash[:16]}...")
        print(f"Scrubbed hash: {scrubbed_hash[:16]}...")

        print(f"\nMessage embedding: ✅ Success")
        print(f"Message extraction (before): ✅ Success")

        if extracted_after is None:
            print(f"Message extraction (after): ✅ Blocked (steganography removed)")
            print(f"\n🎉 OVERALL RESULT: PIPELINE EFFECTIVE")
        else:
            print(f"Message extraction (after): ⚠️  Disrupted (partial success)")
            print(f"\n✅ OVERALL RESULT: PIPELINE MOSTLY EFFECTIVE")

        print(f"\nScrubbed image temporarily available at: {scrubbed_image}")

        # Ask if user wants to save results
        try:
            save_results = input("\nSave test results to current directory? (y/n): ").strip().lower()
            if save_results.startswith('y'):
                # Copy files to current directory
                shutil.copy2(str(steg_image), f"test_with_steganography_{Path(test_image).name}")
                shutil.copy2(scrubbed_image, f"test_scrubbed_{Path(scrubbed_image).name}")
                print("✓ Test files saved to current directory")
        except KeyboardInterrupt:
            print("\nTest completed.")

        return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)