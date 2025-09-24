# Secure Image Processing Pipeline

A hardened image scrubbing workflow designed for human-rights field work. The
pipeline strips metadata, destroys common steganographic payloads, and keeps a
forensic audit trail linking every original image to its obfuscated counterpart.

## Project Goals

* **Source protection** – remove identifying metadata, strip transparency
  channels, and randomize pixel data so LSB payloads cannot survive.
* **Evidence preservation** – preserve originals with cryptographic hashes and
  store detailed audit information in SQLite for legal or research review.
* **Operational usability** – provide a guided Rich-powered CLI that prepares
  the workspace, processes batches, and reports the audit trail in plain
  language.

## Core Components

| Path | Purpose |
| --- | --- |
| `main.py` | Interactive entry point. Handles setup checks, configuration prompts, and runs the batch pipeline. |
| `setup.py` | Initialises the working directories (`ingest/`, `clean/`, `originals/`, `db/`, `logs/`) and the SQLite database. |
| `src/SecurePipeline.py` | Orchestrates ingestion, processing, storage, and audit logging for each batch run. |
| `src/SecureImageProcessor.py` | Performs metadata extraction, multi-pass LSB randomisation, optional noise injection, and format normalisation. |
| `src/DatabaseManager.py` | Creates and manages the SQLite schema used to track runs, files, preserved metadata, and obfuscation details. |
| `test.py` | End-to-end validation script that embeds a known LSB payload, runs the pipeline, and verifies the payload is destroyed. |

The `requirements.txt` file pins the runtime dependencies (Pillow, NumPy, Rich).

## Directory Workflow

The workspace is intentionally segregated:

* `ingest/` – drop sensitive input files here.
* `clean/` – scrubbed images ready for distribution.
* `originals/` – timestamped copies of the untouched originals.
* `db/processing.db` – SQLite audit trail storing run metadata, file hashes, and
  obfuscation summaries.
* `logs/` – reserved for future operational logging.

All directories are created automatically by `setup.py` or during the first run
of `main.py`. You can override their names (and the database filename) with
environment variables such as `PIPELINE_INGEST_DIR`, `PIPELINE_CLEAN_DIR`,
`PIPELINE_DB_FILENAME`, etc. Place overrides in a `.env` file at the project
root for convenience.

## Installation

1. Install Python 3.9 or later.
2. Optionally create a virtual environment and activate it.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Prepare the workspace and database:
   ```bash
   python setup.py
   ```

The setup script is idempotent; rerunning it safely recreates any missing
folders and reinitialises the SQLite schema.

## Running the Pipeline

1. Stage images in the ingest directory.
2. Launch the CLI:
   ```bash
   python main.py
   ```
3. Follow the prompts to select a security level or customise parameters. The
   CLI presents options for LSB flip probability, number of passes, optional
   noise, and output format (JPEG with randomised quality or PNG).
4. Confirm the batch to start processing. The tool displays live progress and
   records each step in the database.
5. Retrieve cleaned files from `clean/` and archive the originals and database
   as required by your operational policy.

### Security Profiles

| Mode | LSB Flip Probability | Passes | Noise | Notes |
| --- | --- | --- | --- | --- |
| Standard | 0.15 | 2 | Enabled | Balanced protection for general use. |
| High | 0.20 | 3 | Enabled | Adds more aggressive LSB disruption. |
| Maximum | 0.25 | 3 | Enabled | Preserves the default behaviour but with additional emphasis on bit randomisation. |
| Custom | 0.05–0.30 | 1–5 | Optional | Fine-grained control over every parameter. |

JPEG output introduces compression artefacts that further disturb frequency
based steganography. PNG output is available for workflows that require
lossless delivery at the expense of reduced obfuscation strength.

## Database & Audit Trail

Every run captures:

* Operator name, configuration JSON, and timestamps.
* SHA-256 hashes, image dimensions, and formats for both original and cleaned
  assets.
* Preserved metadata dumps (EXIF, GPS, ICC profile size, transparency details).
* Obfuscation summaries linking original and cleaned files, including format
  changes and pass counts.
* Action logs documenting preservation, obfuscation, ingest cleanup, and any
  processing errors.

The Rich CLI can show recent run statistics via the “View database summary”
menu option.

## Verification Tools

`test.py` offers an automated confidence check. It creates or accepts an image,
embeds a secret message with a simple LSB algorithm, runs the pipeline in a
temporary workspace, and confirms the message cannot be recovered afterwards.
Run it with:

```bash
python test.py [optional_path_to_image]
```

## Operational Guidance

* Process only material you are authorised to modify; originals contain highly
  sensitive information.
* Scrubbed files no longer match the original hash – this is expected and is
  recorded in the database for forensic integrity.
* Visual content (faces, landmarks) is not altered; pair this tool with
  redaction or blurring where appropriate.
* Protect the database and originals directories as they contain sensitive
  provenance data.

The project prioritises source safety over fidelity, enabling field teams to
share crucial evidence without exposing the individuals who captured it.
