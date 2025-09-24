# Secure Image Processing Pipeline

A specialized tool for protecting human rights workers and investigators by removing identifying information from images through comprehensive metadata stripping and steganographic disruption.

## Overview

This project is designed to clean images of their metadata and disrupt any watermarking and hidden identifiers using LSB obfuscation and file compression. It is a lossy process that modifies the files, so files will fail hash checks after going through this tool.

The pipeline creates an auditable chain of custody while aggressively obfuscating potential identifying information that could compromise sources or reveal sensitive locations.

## Threat Model

### Metadata-Based Identification

Digital images contain extensive metadata that can expose sensitive information:

- **EXIF Data**: Camera make/model, software versions, timestamps, camera settings
- **GPS Coordinates**: Precise location data embedded by cameras and smartphones  
- **IPTC/XMP Tags**: Author information, copyright details, keywords, descriptions
- **ICC Color Profiles**: Device-specific color calibration data that can fingerprint equipment
- **Thumbnail Images**: Often contain unedited versions of cropped or modified images

### Steganographic Threats

Hidden data can be embedded in images through various techniques:

- **LSB Steganography**: Information hidden in least significant bits of pixel data
- **Frequency Domain Hiding**: Data concealed in DCT coefficients (JPEG) or frequency transforms
- **Palette-Based Hiding**: Information embedded in color palette arrangements
- **Alpha Channel Exploitation**: Data hidden in transparency layers
- **Format-Specific Hiding**: Exploitation of format structures (JPEG segments, PNG chunks)

### Digital Watermarking

Invisible identification systems that survive basic editing:

- **Robust Watermarks**: Survive compression, resizing, and minor modifications
- **Fragile Watermarks**: Detect any alteration to the image
- **Semi-Fragile Watermarks**: Survive acceptable modifications but detect malicious changes
- **Spread Spectrum Watermarks**: Distributed across entire image using frequency analysis
- **Machine Learning Watermarks**: AI-generated patterns resistant to detection

### Risks to Human Rights Workers

These identification methods pose serious security risks:

- **Source Identification**: Metadata can reveal the identity of photographers or witnesses
- **Location Tracking**: GPS data and environmental markers can expose sensitive locations
- **Equipment Fingerprinting**: Device-specific signatures can link multiple images to the same person
- **Temporal Analysis**: Timestamp patterns can reveal operational schedules and movements
- **Chain of Custody Exposure**: Processing history can reveal distribution networks
- **Operational Security Compromise**: Hidden identifiers can bypass traditional security measures

## Technical Implementation

### Core Security Measures

**LSB Randomization**
- Randomly flips least significant bits across all color channels
- Uses cryptographically secure random number generation
- Configurable flip probability (5-30%) for varying security levels
- Multi-pass processing to disrupt complex hiding schemes

**Metadata Elimination**
- Complete removal of EXIF, GPS, IPTC, XMP, and ICC profile data
- Preservation of original metadata in secure audit database
- Format normalization to eliminate structure-based hiding

**Steganographic Disruption**
- JPEG compression artifacts break frequency-domain hiding
- Color space conversion disrupts palette-based techniques
- Transparency removal eliminates alpha channel exploitation
- Noise injection defeats correlation-based detection

**Multi-Pass Obfuscation**
- Multiple randomization passes with varying parameters
- Progressive degradation of embedded patterns
- Statistical analysis resistance through randomness accumulation

### Processing Pipeline

1. **Detection Agent**: Scans for supported image formats and validates integrity
2. **Metadata Extraction Agent**: Preserves complete metadata for audit trail
3. **Security Agent**: Applies LSB randomization and noise injection
4. **Sanitization Agent**: Strips metadata and normalizes format
5. **Storage Agent**: Creates timestamped preservation copies
6. **Audit Agent**: Maintains immutable processing records

### Evidence Preservation

The system maintains forensic integrity while protecting operational security:

- **Original Preservation**: Bit-for-bit copies with cryptographic verification
- **Complete Audit Trail**: SQLite database with full processing history
- **Chain of Custody**: Links between original and processed images
- **Operator Identification**: All actions attributed to authenticated users
- **Configuration Logging**: Processing parameters recorded for reproducibility

## Installation

### Prerequisites

- Python 3.7 or higher
- Required packages: Pillow, NumPy

### Setup

1. Clone or download the project files
2. Install dependencies:
   ```
   pip install Pillow numpy
   ```
3. Run initial setup:
   ```
   python run_setup.py
   ```

This creates the required directory structure:
- `images_ingest/` - Input folder for sensitive images
- `images_clean/` - Output folder for processed images  
- `images_originals/` - Preserved original files
- `db/` - SQLite audit database
- `logs/` - Processing logs

## Usage

### Interactive Processing

1. Place sensitive images in the `images_ingest/` folder
2. Run the main application:
   ```
   python main.py
   ```
3. Configure security parameters through interactive prompts
4. Review files to be processed and confirm operation
5. Retrieve cleaned images from `images_clean/` folder

### Security Levels

**Standard Mode** (Default)
- 15% LSB flip probability
- 2 obfuscation passes
- Complete metadata removal
- JPEG output with quality 85

**High Security Mode**  
- 20% LSB flip probability
- 3 obfuscation passes
- Noise injection enabled
- Progressive JPEG encoding

**Maximum Security Mode**
- 25% LSB flip probability  
- 3+ obfuscation passes
- Multi-bit randomization
- Aggressive noise disruption

**Custom Mode**
- User-configurable parameters
- Variable pass count (1-5)
- Adjustable flip probability (5-30%)
- Format selection options

## Important Security Considerations

### Operational Security

- Only process images you have explicit permission to modify
- Original files are preserved but contain sensitive metadata
- Secure deletion of `images_originals/` may be required based on threat model
- Database contains complete processing history and should be protected accordingly

### Limitations

- Cannot detect or remove unknown steganographic methods
- Some watermarking techniques may survive processing
- Visual inspection may still reveal identifying features
- Does not address content-based identification (facial recognition, landmarks)

### Legal and Ethical Use

This tool is intended for:
- Protection of human rights sources and witnesses
- Journalist source protection in hostile environments  
- Activist operational security in authoritarian contexts
- Legal evidence processing with proper chain of custody

### File Integrity Warning

Processed images will fail hash verification against originals. This is intentional and necessary for security. The audit database maintains cryptographic hashes of both original and processed files for verification purposes.

## Database Schema

The SQLite audit database maintains:

- **Processing Runs**: Timestamps, operators, configurations, statistics
- **File Records**: Original and cleaned file information with hashes  
- **Metadata Preservation**: Complete EXIF/GPS/IPTC data from originals
- **Processing Actions**: Detailed log of all operations performed
- **Obfuscation Summary**: Security measures applied to each image
- **File Relationships**: Links between original and processed files

## Directory Structure

```
project/
├── main.py                    # Interactive processing interface
├── run_setup.py              # Standalone setup script  
├── setup.py                  # Setup module
├── config.json               # Configuration templates
├── src/
│   ├── SecurePipeline.py     # Main pipeline orchestrator
│   ├── SecureImageProcessor.py # Core obfuscation engine
│   └── DatabaseManager.py    # SQLite audit trail
├── images_ingest/            # Input: sensitive images
├── images_clean/             # Output: processed images
├── images_originals/         # Preserved originals
├── db/                       # SQLite database
└── logs/                     # Processing logs
```

## Technical Requirements

- **Python Version**: 3.7+
- **Memory**: Sufficient for largest image in batch
- **Storage**: 3x image size (original + processed + preserved copy)
- **Permissions**: Read/write access to all directories
- **Platform**: Cross-platform (Windows, macOS, Linux)

## Threat Coverage

This tool addresses the following identification vectors:

- Camera fingerprinting through metadata removal
- GPS tracking through coordinate stripping
- Steganographic payloads through LSB randomization  
- Invisible watermarks through multi-pass obfuscation
- Format-based hiding through normalization
- Palette steganography through RGB conversion
- Transparency exploitation through alpha channel removal

## Forensic Compliance

The audit trail maintains evidence standards:

- Immutable database records with foreign key constraints
- Cryptographic hash verification for all files
- Complete metadata preservation for legal requirements  
- Operator identification and timestamp precision
- Configuration documentation for reproducibility
- Error logging with detailed failure analysis