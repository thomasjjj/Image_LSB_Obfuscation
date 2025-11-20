#!/usr/bin/env python3

import os
import io
import uuid
from pathlib import Path
from typing import List

import streamlit as st
from pathlib import Path
import sys

# Ensure 'src' is on path for secure_pipeline package
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from Image_LSB.secure_pipeline import SecurePipeline
from Image_LSB.secure_image_processor import SecureImageProcessor
import setup as setup_module


PROJECT_ROOT = Path(__file__).resolve().parent


def ensure_workspace() -> Path:
    """Create an isolated workspace for this UI session."""
    ws_root = PROJECT_ROOT / ".ui_workspace"
    ws_root.mkdir(exist_ok=True)
    session_dir = ws_root / f"session_{uuid.uuid4().hex[:8]}"
    session_dir.mkdir(parents=True, exist_ok=True)
    # Initialize standard structure + DB
    setup_module.run_setup(base_dir=session_dir)
    return session_dir


def save_uploads(ingest_dir: Path, uploads: List[st.runtime.uploaded_file_manager.UploadedFile]) -> List[Path]:
    saved: List[Path] = []
    for uf in uploads:
        # Sanitize filename (basic)
        name = Path(uf.name).name
        target = ingest_dir / name
        with open(target, "wb") as f:
            f.write(uf.getbuffer())
        saved.append(target)
    return saved


def main() -> None:
    st.set_page_config(page_title="Secure Media Pipeline", layout="wide")
    st.title("Secure Media Processing Pipeline")
    st.caption("Auditable obfuscation for images; metadata stripping for MP4 videos.")

    with st.sidebar:
        st.header("Settings")
        operator = st.text_input("Operator name", value=os.getenv("PIPELINE_DEFAULT_OPERATOR", "Anonymous"))

        st.subheader("Security Profile")
        preset = st.selectbox("Preset", [
            "1 – Standard (p=0.15, 2 passes, noise)",
            "2 – High (p=0.20, 3 passes, noise)",
            "3 – Maximum (p=0.25, 3 passes, noise)",
            "4 – Custom",
        ], index=int(os.getenv("PIPELINE_DEFAULT_SECURITY_LEVEL", "1")) - 1)

        lsb_prob = 0.15
        passes = 2
        add_noise = True
        if preset.startswith("2"):
            lsb_prob, passes = 0.20, 3
        elif preset.startswith("3"):
            lsb_prob, passes, add_noise = 0.25, 3, True
        elif preset.startswith("4"):
            lsb_prob = st.slider("LSB flip probability", 0.05, 0.30, 0.15, 0.01)
            passes = st.slider("Obfuscation passes", 1, 5, 2, 1)
            add_noise = st.toggle("Add noise", True)

        st.subheader("Output")
        ofmt = st.radio("Format", ["JPEG", "PNG"], index=0)
        jpeg_quality = 85
        if ofmt == "JPEG":
            jpeg_quality = st.slider("JPEG quality", 70, 95, 85, 1)

        st.divider()
        st.write("MP4 videos: metadata is stripped only — no LSB randomization.")

    uploads = st.file_uploader(
        "Drop images/videos here (JPEG, PNG, BMP, TIFF, WebP, MP4)",
        type=["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp", "mp4"],
        accept_multiple_files=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        run_btn = st.button("Process", type="primary", use_container_width=True, disabled=not uploads)
    with col2:
        clear_btn = st.button("Clear", use_container_width=True)

    if clear_btn:
        st.experimental_rerun()

    if run_btn and uploads:
        # Prepare isolated workspace
        ws = ensure_workspace()
        ingest_dir = ws / os.getenv("PIPELINE_INGEST_DIR", "ingest")
        clean_dir = ws / os.getenv("PIPELINE_CLEAN_DIR", "clean")

        saved_paths = save_uploads(ingest_dir, uploads)
        if not saved_paths:
            st.warning("No files saved. Please try again.")
            return

        # Initialize pipeline with UI config
        pipeline = SecurePipeline(str(ws))
        pipeline.config.update({
            'operator_name': operator,
            'lsb_flip_probability': float(lsb_prob),
            'obfuscation_passes': int(passes),
            'add_noise': bool(add_noise),
            'output_format': ofmt,
            'jpeg_quality': int(jpeg_quality),
        })
        pipeline.processor = SecureImageProcessor(pipeline.config)

        # Pre-flight ffmpeg check
        have_videos = any(p.suffix.lower() == ".mp4" for p in saved_paths)
        ffmpeg_ok = pipeline.video_processor.ffmpeg_available()
        if have_videos and not ffmpeg_ok:
            st.warning("ffmpeg not found — MP4 files will be skipped. Install ffmpeg and ensure it's on PATH.")

        # Start run
        run_id = pipeline.db.start_run(pipeline.config['operator_name'], pipeline.config)

        overall = st.progress(0, text="Starting…")
        status_area = st.container()

        media_files = pipeline.scan_ingest_folder()
        total = len(media_files)
        stats = {'total': total, 'successful': 0, 'failed': 0}

        for idx, mf in enumerate(media_files, start=1):
            overall.progress(min(int(idx * 100 / total), 100), text=f"Processing {mf.name} ({idx}/{total})")
            try:
                ok = False
                if mf.suffix.lower() == '.mp4':
                    if ffmpeg_ok:
                        ok = pipeline.process_single_video(mf, run_id, progress=None)
                    else:
                        ok = False
                        with status_area:
                            st.error(f"Skipped video (ffmpeg missing): {mf.name}")
                else:
                    ok = pipeline.process_single_image(mf, run_id, progress=None)

                if ok:
                    stats['successful'] += 1
                    with status_area:
                        st.success(f"Processed: {mf.name}")
                else:
                    stats['failed'] += 1
                    with status_area:
                        st.error(f"Failed: {mf.name}")
            except Exception as e:  # noqa: BLE001 – show in UI
                stats['failed'] += 1
                with status_area:
                    st.exception(e)

        pipeline.db.finish_run(run_id, stats)
        overall.progress(100, text="Complete")

        st.subheader("Results")
        st.write(f"Total: {stats['total']} • Success: {stats['successful']} • Failed: {stats['failed']}")

        cleaned = sorted([p for p in clean_dir.glob('*') if p.is_file()])
        if cleaned:
            for cp in cleaned:
                with open(cp, 'rb') as f:
                    data = f.read()
                st.download_button(
                    label=f"Download {cp.name}",
                    data=data,
                    file_name=cp.name,
                    mime=("video/mp4" if cp.suffix.lower() == ".mp4" else None),
                    use_container_width=True,
                )
        else:
            st.info("No cleaned outputs produced.")


if __name__ == "__main__":
    main()
