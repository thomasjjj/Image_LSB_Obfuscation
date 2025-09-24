# AGENTS.md — Secure Image Processing Pipeline (Human Rights Protection)

## Purpose

Provide a **secure, auditable, and automated** workflow to protect sources and researchers in human rights documentation by aggressively obfuscating potential identifying information in images. The system:

* **Preserves originals** with cryptographic hashes and complete metadata extraction for legal/forensic purposes.
* **Applies LSB randomization** to disrupt steganographic content and hidden watermarks.
* **Strips all metadata** (EXIF/GPS/IPTC/XMP/ICC profiles) and normalizes image format.
* **Maintains full audit trail** in SQLite database linking original ↔ cleaned files with processing details.

## Core Security Goals

* **Source Protection**: Remove identifying metadata that could compromise sources or locations.
* **Steganographic Disruption**: LSB randomization to defeat common hiding techniques.  
* **Watermark Obfuscation**: Multi-pass processing to disrupt embedded identification.
* **Evidence Preservation**: Complete audit trail while protecting sensitive information.

---

## High-Level Flow

```
[ingest/]  -->  Detection Agent     -->  Load & analyze image
                                   -->  Metadata Extraction Agent (preserve complete metadata)
                                   -->  Security Agent (LSB randomization, multi-pass obfuscation)
                                   -->  Sanitization Agent (strip metadata, format normalization)  
                                   -->  Storage Agent (save to clean/, move original to originals/)
                                   -->  Audit Agent (SQLite logging with full provenance)
```

### Directory Layout
* `ingest/` — Drop sensitive images here (auto-detected).
* `clean/` — Secure, obfuscated outputs ready for publication/distribution.
* `originals/` — Time-stamped preserved originals (YYYYMMDDThhmmssZ__filename).
* `db/` — `processing.db` (SQLite audit database).

---

## Agent Responsibilities

### 1) Detection Agent
* Scans `ingest/` for new image files (JPEG, PNG, BMP, TIFF, WEBP).
* Validates file integrity and format support.
* Initiates processing run with operator authentication.

### 2) Metadata Extraction Agent
* **Comprehensive extraction**: EXIF (including GPS), IPTC, XMP, ICC profiles.
* **Risk assessment**: Identifies transparency channels, palette modes, unusual metadata.
* **Database preservation**: Stores complete metadata dump for legal/forensic needs.
* Calculates SHA-256 hash of original file.

### 3) Security Agent (Core Obfuscation)
* **LSB Randomization**: Randomly flips least significant bits across all color channels.
* **Multi-pass processing**: 2-3 passes with varying flip probabilities (15-25%).
* **Noise injection**: Subtle random noise to disrupt frequency-domain hiding.
* **2nd LSB targeting**: Optional second-bit randomization for aggressive mode.
* **Format disruption**: JPEG compression artifacts to break steganographic patterns.

### 4) Sanitization Agent  
* **Complete metadata removal**: Zero EXIF/GPS/IPTC/XMP/ICC data in output.
* **Transparency elimination**: Converts RGBA → RGB with white background.
* **Color space normalization**: Forces RGB mode regardless of input.
* **Format standardization**: Outputs JPEG with randomized quality (70-95%).

### 5) Storage Agent
* Creates timestamped copy in `originals/` before processing.
* Saves cleaned version to `clean/` with secure filename.
* Removes processed file from `ingest/` only after successful completion.
* Maintains strict separation: never modifies files in place.

### 6) Audit Agent  
* **Complete provenance**: Links every original to its cleaned counterpart.
* **Processing details**: Records LSB flip probability, passes applied, metadata removed.
* **Action timeline**: Timestamps every operation with operator identification.
* **Hash verification**: SHA-256 for both original and cleaned versions.
* **Immutable logging**: Append-only database records for forensic integrity.

---

## Security Configuration

### Standard Mode (Default)
* 15% LSB flip probability
* 2 obfuscation passes  
* Complete metadata removal
* JPEG output with quality 85

### High Security Mode
* 20% LSB flip probability
* 3 obfuscation passes
* Noise injection enabled
* Progressive JPEG encoding

### Maximum Security Mode  
* 25% LSB flip probability
* 3+ obfuscation passes
* 2nd LSB randomization
* Aggressive noise disruption
* Quality randomization

### Custom Mode
* User-configurable flip probability (5-30%)
* Variable pass count (1-5)
* Selective noise application
* Format options (JPEG/PNG)

---

## Database Schema (Core Tables)

### Processing Runs
```sql
runs (run_id, started_at_utc, operator_name, total_files, successful_files, configuration_json)
```

### File Tracking  
```sql
files (file_id, run_id, file_type[original|cleaned], original_filename, stored_path, file_hash_sha256, image_format, created_at_utc)
```

### Metadata Preservation
```sql
preserved_metadata (file_id, exif_data_json, exif_gps_json, icc_profile_size, had_transparency, original_mode)
```

### Security Summary
```sql
obfuscation_summary (cleaned_file_id, lsb_randomization_applied, obfuscation_passes, lsb_flip_probability, metadata_stripped, format_changed)
```

### Audit Trail
```sql  
processing_actions (action_id, run_id, file_id, action_type, action_details_json, timestamp_utc)
file_relationships (original_file_id, cleaned_file_id)
```

---

## Interactive Operation

### User Interface Flow
1. **Configuration Setup**: Interactive prompts for security level and operator identification.
2. **Batch Detection**: Automatic scanning of `ingest/` folder.
3. **Processing Confirmation**: User reviews files to be processed.
4. **Real-time Feedback**: Progress updates with security measures applied.
5. **Completion Summary**: Statistics and verification information.

### No Command-Line Arguments
* Fully interactive guided interface
* Context-sensitive prompts
* Built-in help and explanations
* Error recovery and user guidance

---

## Security Assurance

### Protection Mechanisms
* **LSB disruption** defeats most steganographic hiding
* **Multi-pass randomization** prevents pattern recovery  
* **Metadata elimination** removes identifying information
* **Format normalization** adds compression artifacts
* **Hash verification** ensures processing integrity

### Evidence Preservation
* **Original files untouched** until successful processing
* **Complete metadata backup** for legal requirements
* **Cryptographic hashes** for file integrity
* **Immutable audit logs** for forensic analysis
* **Full provenance chain** from source to cleaned output

### Threat Model Coverage
* **Camera fingerprinting** → Metadata removal
* **GPS tracking** → EXIF/GPS stripping  
* **Steganographic payloads** → LSB randomization
* **Invisible watermarks** → Multi-pass obfuscation
* **Format-based hiding** → Normalization to JPEG
* **Palette steganography** → RGB conversion
* **Transparency hiding** → Alpha channel removal

---

## Implementation Notes

* **Pure Python**: PIL/Pillow + NumPy only, no external dependencies.
* **Cross-platform**: Windows, macOS, Linux compatibility.
* **Memory efficient**: Processes images individually, suitable for large batches.
* **Error resilient**: Individual file failures don't stop batch processing.
* **Database integrity**: WAL mode with foreign key constraints.

---

## Operational Security

### File Handling
* **Atomic operations**: Complete processing or no changes
* **Secure deletion**: Original files removed only after verification
* **Path validation**: Prevents directory traversal attacks
* **Extension verification**: Validates file types before processing

### Audit Requirements
* **Operator identification**: All actions tied to authenticated user
* **Timestamp precision**: UTC timestamps for all operations  
* **Configuration logging**: Processing parameters recorded for reproducibility
* **Error documentation**: Failed operations logged with details

---

## Deployment Checklist

### Initial Setup
- [ ] Create directory structure (`ingest/`, `clean/`, `originals/`, `db/`)
- [ ] Install Python dependencies (`pip install Pillow numpy`)
- [ ] Verify write permissions on all directories
- [ ] Test database creation and access

### Security Verification  
- [ ] Confirm LSB randomization is applied (visual/statistical tests)
- [ ] Verify complete metadata removal (`exiftool` verification)
- [ ] Test hash calculation accuracy
- [ ] Validate audit trail completeness

### Operational Testing
- [ ] Process test images with known metadata
- [ ] Verify original preservation integrity  
- [ ] Test batch processing with mixed formats
- [ ] Confirm error handling and recovery

---

## Legal & Ethical Considerations

**Intended Use**: Protection of human rights sources, journalists, and activists working in sensitive environments.

**Evidence Integrity**: Complete preservation of original files with cryptographic verification maintains legal admissibility while protecting operational security.

**Source Protection**: Aggressive metadata removal and steganographic disruption specifically designed to prevent source identification and location tracking.

**Audit Compliance**: Full database logging provides accountability while maintaining operational security for sensitive documentation work.

---

### Final Notes

This pipeline prioritizes **source protection over convenience** — designed specifically for high-risk human rights documentation where source safety is paramount. The comprehensive obfuscation techniques may exceed typical sanitization needs but are appropriate for protecting vulnerable sources and researchers in hostile environments.

Every design decision balances **maximum security** with **evidence preservation**, ensuring both operational protection and legal/forensic integrity.