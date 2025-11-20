# Secure Media Processing Pipeline

A secure, auditable pipeline to obfuscate images (metadata stripping + multi-pass LSB randomization) and strip metadata from MP4 videos. Originals are preserved and a SQLite audit trail records actions and hashes.

- Source protection: remove EXIF/GPS, strip transparency, randomize LSBs.
- Evidence preservation: preserve originals, record hashes and actions.
- Operational usability: CLI and Streamlit UI with progress and logs.

## Install

Requires Python 3.9+.

- From source (dev):
  - Create and activate a virtualenv.
  - pip install -r requirements-dev.txt

- As a package:
  - pip install .

Console script installed: `image-lsb`

## Using the Library

```python
from Image_LSB import image_clean, video_clean

# Clean an image on disk and save output
cleaned_img, log, out_path = image_clean(
    "ingest/photo.jpg",
    lsb_flip_probability=0.20,
    obfuscation_passes=3,
    add_noise=True,
    output_format="JPEG",
    jpeg_quality=85,
    output_dir="clean",
)

# Clean a loaded Pillow image in memory (no file written)
from PIL import Image
im = Image.open("photo.png")
clean_im, log, out_path = image_clean(im)

# Strip metadata from a video (no LSB; requires ffmpeg)
out_video, details = video_clean("clips/source.mp4", output_dir="clean")
```

Defaults (image_clean):
- lsb_flip_probability=0.15 (recommended 0.05–0.30)
- obfuscation_passes=2 (1–5)
- add_noise=True
- output_format="JPEG", jpeg_quality=85

For video_clean, only metadata is stripped; LSB is not applied.

## CLI Usage

Two entry points:
- Package script: `image-lsb`
- Repo launcher: `python main.py`

Workflow:
1. Place media in `ingest/` (JPG/PNG/BMP/TIFF/WebP; MP4).
2. Run the CLI and choose a preset or custom options.
3. Originals preserved to `originals/`, cleaned outputs to `clean/`, audit DB at `db/processing.db`.
4. ffmpeg is required for MP4; if missing, videos are skipped.

## Streamlit UI

Run a drag-and-drop UI with progress and downloads:

```bash
streamlit run streamlit_app.py
```

The UI uses an isolated workspace per session and the same processing logic.

## Directories and Configuration

Default structure:

```
ingest/      # drop sensitive originals here
clean/       # scrubbed outputs
originals/   # timestamped, immutable copies of originals
db/          # SQLite audit log (processing.db)
logs/        # reserved for operational logging
```

Environment overrides (CLI/setup):
- PIPELINE_INGEST_DIR (default: "ingest")
- PIPELINE_CLEAN_DIR ("clean")
- PIPELINE_ORIGINALS_DIR ("originals")
- PIPELINE_DB_DIR ("db")
- PIPELINE_LOG_DIR ("logs")
- PIPELINE_DB_FILENAME ("processing.db")
- PIPELINE_DEFAULT_SECURITY_LEVEL (1–4)
- Optional fine-tuning: PIPELINE_LSB_FLIP_PROBABILITY, PIPELINE_OBFUSCATION_PASSES, PIPELINE_ADD_NOISE, PIPELINE_OUTPUT_FORMAT, PIPELINE_JPEG_QUALITY

Place overrides in a `.env` at repo root to persist.

## Database & Audit Trail (CLI)

The CLI records:
- Runs: operator, timestamps, config, totals.
- Files: hashes, sizes, dimensions, formats.
- Preserved metadata: EXIF/GPS/ICC/transparency.
- Obfuscation summary: metadata removal, pass counts, noise, format changes.
- Actions: preservation, processing, ingest cleanup, errors.

## Tests & CI

Run tests locally:

```bash
pip install -r requirements-dev.txt
pytest -q
```

GitHub Actions workflow `.github/workflows/ci.yml` runs tests on pushes and PRs.

## Documentation

API and usage documentation is built with Sphinx and published via GitHub Pages.

- Live docs (after Pages is enabled): https://<your-org>.github.io/<your-repo>/
- Build locally:
  - pip install -r requirements-dev.txt
  - sphinx-build -b html docs/source docs/_build/html
  - open docs/_build/html/index.html

## Notes

- ffmpeg must be installed and on PATH for MP4 processing.
- Visual anonymisation (faces/redaction) is out of scope; pair with dedicated tools.

## API Docs (Optional)

The primary API is small and documented via docstrings. If you’d like generated docs (Sphinx/Markdown), open an issue and we can add a docs/ folder and CI job to publish.
