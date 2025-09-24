# AGENTS.md — Secure Image Processing Pipeline

## Mission

Deliver a **secure, auditable, and automated** workflow that protects sources
and researchers by aggressively obfuscating sensitive imagery while preserving a
verifiable chain of custody. The system pairs LSB randomisation with thorough
metadata stripping and detailed audit logging.

---

## Current Code Surface

| File | Role |
| --- | --- |
| `main.py` | Rich-powered CLI for configuration, batch execution, and quick database summaries. |
| `setup.py` | Idempotent workspace bootstrapper – creates `ingest/`, `clean/`, `originals/`, `db/`, `logs/`, and seeds the SQLite schema. |
| `src/SecurePipeline.py` | Orchestrates ingestion, preservation, obfuscation, storage, and audit logging. |
| `src/SecureImageProcessor.py` | Handles metadata extraction, multi-pass LSB randomisation, optional noise injection, and format normalisation. |
| `src/DatabaseManager.py` | Encapsulates all SQLite interactions (runs, files, preserved metadata, obfuscation summaries, actions). |
| `test.py` | Optional verification harness that embeds and then attempts to recover an LSB payload to prove the scrubber succeeds. |

Dependencies are pinned in `requirements.txt` (`rich`, `pillow`, `numpy`). The
system remains pure Python and cross-platform.

---

## Directory Expectations

The working tree is designed around strict segregation:

```
project/
├── ingest/       # Drop sensitive originals here for processing
├── clean/        # Scrubbed outputs safe for distribution
├── originals/    # Timestamped, immutable copies of the originals
├── db/           # Contains processing.db audit log (WAL mode + FK constraints)
├── logs/         # Reserved for operational logging
└── src/          # Pipeline modules listed above
```

`setup.py` and the first run of `main.py` ensure these folders exist. Directory
names, the database filename, and other defaults can be overridden through
environment variables (`PIPELINE_INGEST_DIR`, `PIPELINE_CLEAN_DIR`,
`PIPELINE_DB_FILENAME`, etc.). Use a `.env` file in the repo root to persist
custom settings.

---

## Operational Flow

1. **Setup** – run `python setup.py` (idempotent) to create directories and
   initialise `processing.db`.
2. **Ingest** – copy files into `ingest/`.
3. **Configure** – launch `python main.py`, authenticate via operator name, and
   choose a security preset or custom parameters.
4. **Process** – the pipeline preserves originals, extracts metadata, applies
   multi-pass LSB randomisation (plus optional noise), strips metadata, and saves
   a cleaned copy.
5. **Audit** – every step is captured: hashes, metadata dumps, obfuscation
   summaries, and actions linking originals to cleaned files.

The CLI exposes a database summary view for quick run statistics.

---

## Security Profiles (CLI Presets)

| Level | LSB Probability | Passes | Noise | Notes |
| --- | --- | --- | --- | --- |
| 1 – Standard | 0.15 | 2 | Enabled | Balanced disruption for routine releases. |
| 2 – High | 0.20 | 3 | Enabled | Higher certainty against stubborn LSB payloads. |
| 3 – Maximum | 0.25 | 3 | Enabled | Most aggressive default. Consider enabling 2nd-bit targeting manually if extended. |
| 4 – Custom | 0.05–0.30 | 1–5 | Optional | Exposes raw configuration prompts for bespoke missions. |

JPEG output (default) adds compression artefacts that further disrupt
frequency-domain techniques. PNG output is available when lossless delivery is
mandatory.

---

## Database Overview

`DatabaseManager` creates the following tables (WAL mode, FK constraints):

* `runs` – operator, timestamps, configuration JSON, success/failure counts.
* `files` – each original and cleaned asset with hashes, dimensions, formats.
* `file_relationships` – links originals to their cleaned counterparts.
* `preserved_metadata` – EXIF/GPS dumps, ICC profile size, transparency status.
* `processing_actions` – chronological log of preservation, obfuscation, ingest
  cleanup, and error events.
* `obfuscation_summary` – records metadata removal, pass counts, noise usage, and
  format changes.

---

## Testing & Validation

Run `python test.py` to perform an end-to-end confidence check. The script embeds
an LSB message, processes it using the production classes, and verifies the
payload cannot be recovered afterwards.

---

## Security & Ethics

* Originals and the audit database are sensitive artefacts – protect and, when
  necessary, securely delete them according to your operational doctrine.
* Visual anonymisation (face blurring, redaction) is outside the scope of this
  pipeline; pair with dedicated tools when content-based identifiers must be
  removed.
* Intended for human-rights, journalistic, or activist work where preserving
  evidence while protecting sources is paramount. Ensure usage complies with
  local laws and organisational policies.

The design prioritises **maximum source safety** without sacrificing forensic
integrity, enabling teams to publish critical evidence while shielding the people
who captured it.
