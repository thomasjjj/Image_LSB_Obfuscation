#!/usr/bin/env python3

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

from rich.console import Console
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from . import (
    image_clean,
    video_clean,
    SecureImageProcessor,
    DatabaseManager,
)


console = Console()
print = console.print  # type: ignore[assignment]


def _workspace_directory_names() -> List[str]:
    return [
        os.getenv("PIPELINE_INGEST_DIR", "ingest"),
        os.getenv("PIPELINE_CLEAN_DIR", "clean"),
        os.getenv("PIPELINE_ORIGINALS_DIR", "originals"),
        os.getenv("PIPELINE_DB_DIR", "db"),
        os.getenv("PIPELINE_LOG_DIR", "logs"),
    ]


def prompt(message: str) -> str:
    return console.input(f"[bold cyan]{escape(message)}[/]")


def show_welcome_message() -> None:
    print("=" * 60, style="bold cyan")
    print("SECURE MEDIA PROCESSING PIPELINE", style="bold white")
    print("Human Rights Documentation Tool", style="bold white")
    print("=" * 60, style="bold cyan")
    print()
    print("This tool securely processes sensitive media by:", style="bold")
    print("• Removing all metadata (EXIF, GPS, etc.)", style="green")
    print("• Applying LSB randomization to disrupt hidden content (images only)", style="green")
    print("• Preserving originals with complete audit trail", style="green")
    print("• Creating clean versions safe for distribution", style="green")
    print()


def ensure_workspace(base_dir: Path) -> None:
    for dirname in _workspace_directory_names():
        (base_dir / dirname).mkdir(parents=True, exist_ok=True)


def scan_ingest(ingest_dir: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".mp4"}
    items: List[Path] = []
    for p in ingest_dir.iterdir():
        if p.is_file() and p.suffix.lower() in exts:
            items.append(p)
    return sorted(items)


def choose_configuration() -> Dict:
    config = {
        "operator_name": os.getenv("PIPELINE_DEFAULT_OPERATOR", "Anonymous"),
        "lsb_flip_probability": 0.15,
        "obfuscation_passes": 2,
        "add_noise": True,
        "output_format": "JPEG",
        "jpeg_quality": 85,
    }

    print("\n[bold]Operator:[/]")
    name = prompt(f"Your operator name [{config['operator_name']}]: ").strip() or config["operator_name"]
    config["operator_name"] = name

    print("\n[bold]Security profile:[/]")
    print("1. Standard (p=0.15, 2 passes, noise)")
    print("2. High (p=0.20, 3 passes, noise)")
    print("3. Maximum (p=0.25, 3 passes, noise)")
    print("4. Custom")
    level = prompt("Choose level (1-4) [1]: ").strip() or "1"
    if level == "2":
        config.update({"lsb_flip_probability": 0.20, "obfuscation_passes": 3})
    elif level == "3":
        config.update({"lsb_flip_probability": 0.25, "obfuscation_passes": 3, "add_noise": True})
    elif level == "4":
        try:
            p = prompt(f"LSB flip probability (0.05-0.30) [{config['lsb_flip_probability']}]: ").strip()
            if p:
                config["lsb_flip_probability"] = max(0.05, min(0.30, float(p)))
            n = prompt(f"Obfuscation passes (1-5) [{config['obfuscation_passes']}]: ").strip()
            if n:
                config["obfuscation_passes"] = max(1, min(5, int(n)))
            noise_default = "y" if config["add_noise"] else "n"
            noise = prompt(f"Add noise? (y/n) [{noise_default}]: ").strip().lower()
            if noise:
                config["add_noise"] = not noise.startswith("n")
        except ValueError:
            print("[bold red]Invalid input; using defaults.[/]")

    print("\n[bold]Output format:[/]")
    print("1. JPEG (recommended)")
    print("2. PNG (lossless)")
    fmt = prompt("Choose format (1-2) [1]: ").strip() or "1"
    config["output_format"] = "PNG" if fmt == "2" else "JPEG"
    if config["output_format"] == "JPEG":
        q = prompt(f"JPEG quality (70-95) [{config['jpeg_quality']}]: ").strip()
        if q:
            try:
                config["jpeg_quality"] = max(70, min(95, int(q)))
            except ValueError:
                print("[bold red]Invalid quality; keeping default.[/]")

    print("\n[bold cyan]=== CONFIGURATION SUMMARY ===[/]")
    for k in ["operator_name", "lsb_flip_probability", "obfuscation_passes", "add_noise", "output_format", "jpeg_quality"]:
        print(f"{k}: {config.get(k)}")

    confirm = prompt("Proceed with this configuration? (y/n) [y]: ").strip().lower()
    if confirm.startswith("n"):
        print("[bold red]Configuration cancelled.[/]")
        sys.exit(0)

    return config


def process_batch(base_dir: Path, config: Dict) -> None:
    dirs = {
        "ingest": base_dir / os.getenv("PIPELINE_INGEST_DIR", "ingest"),
        "clean": base_dir / os.getenv("PIPELINE_CLEAN_DIR", "clean"),
        "originals": base_dir / os.getenv("PIPELINE_ORIGINALS_DIR", "originals"),
        "db": base_dir / os.getenv("PIPELINE_DB_DIR", "db"),
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    db_path = dirs["db"] / os.getenv("PIPELINE_DB_FILENAME", "processing.db")
    db = DatabaseManager(str(db_path))

    media_files = scan_ingest(dirs["ingest"])
    if not media_files:
        print("[bold yellow]No supported media found in ingest folder.[/]")
        return

    videos = [p for p in media_files if p.suffix.lower() == ".mp4"]
    images = [p for p in media_files if p.suffix.lower() != ".mp4"]

    from .secure_video_processor import SecureVideoProcessor
    vproc = SecureVideoProcessor()
    ffmpeg_ok = vproc.ffmpeg_available()
    files_to_process = list(media_files)
    if videos and not ffmpeg_ok:
        print("[bold yellow]ffmpeg not found on PATH — MP4 videos will be skipped.[/]")
        print("To enable video processing, install ffmpeg and ensure it's on PATH.")
        files_to_process = images
        if not files_to_process:
            print("[bold yellow]Only videos detected and ffmpeg is missing. Nothing to process.[/]")
            return

    print(f"\n[bold]Found {len(files_to_process)} file(s) to process:[/]")
    for mf in files_to_process:
        print(f"  - {escape(mf.name)}", style="dim")

    proceed = prompt(f"\nProcess all {len(files_to_process)} files? (y/n) [y]: ").strip().lower()
    if proceed.startswith("n"):
        print("[bold yellow]Processing cancelled.[/]")
        return

    run_id = db.start_run(config["operator_name"], config)
    stats = {"total": len(files_to_process), "successful": 0, "failed": 0}

    hasher = SecureImageProcessor(config)

    progress_columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    ]

    with Progress(*progress_columns, console=console, transient=True) as progress:
        task_id = progress.add_task("Processing media", total=len(files_to_process))
        for mf in files_to_process:
            progress.update(task_id, description=f"Processing {escape(mf.name)}")
            try:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                original_filename = f"{timestamp}__{mf.name}"
                original_path = dirs["originals"] / original_filename
                shutil.copy2(mf, original_path)

                # File hash and size
                original_hash = hasher.calculate_file_hash(str(mf))
                original_info = {
                    "width": 0,
                    "height": 0,
                    "format": mf.suffix.upper().lstrip("."),
                    "mode": "",
                    "file_size": mf.stat().st_size,
                }

                # For images, open to extract dimensions and metadata
                preserved_metadata = {
                    "exif_data": {},
                    "exif_gps": {},
                    "icc_profile": 0,
                    "other_info": {"media_type": "video_mp4" if mf.suffix.lower() == ".mp4" else "image"},
                    "has_transparency": False,
                    "original_mode": "",
                }
                if mf.suffix.lower() != ".mp4":
                    from PIL import Image
                    with Image.open(mf) as im:
                        original_info.update({
                            "width": im.width,
                            "height": im.height,
                            "format": im.format,
                            "mode": im.mode,
                        })
                        preserved_metadata = hasher.extract_all_metadata(im)

                original_file_id = db.record_file(
                    run_id, "original", mf.name, str(original_path), original_hash, original_info
                )
                db.record_preserved_metadata(original_file_id, preserved_metadata)
                db.record_action(run_id, original_file_id, "preserve_original", {
                    "original_path": str(mf),
                    "preserved_path": str(original_path),
                    "hash_sha256": original_hash,
                })

                # Process via exported API
                if mf.suffix.lower() == ".mp4":
                    clean_path, details = video_clean(mf, output_dir=dirs["clean"], filename_suffix="_clean")
                    obfuscation_log = {
                        "metadata_stripped": True,
                        "lsb_randomization_applied": False,
                        "transparency_removed": False,
                        "noise_added": False,
                        "passes_applied": 0,
                    }
                    cleaned_format = "MP4"
                else:
                    _, obfuscation_log, clean_path = image_clean(
                        mf,
                        lsb_flip_probability=config["lsb_flip_probability"],
                        obfuscation_passes=config["obfuscation_passes"],
                        add_noise=config["add_noise"],
                        output_format=config["output_format"],
                        jpeg_quality=config["jpeg_quality"],
                        output_dir=dirs["clean"],
                    )
                    cleaned_format = config["output_format"]

                if clean_path is None:
                    raise RuntimeError("Cleaned output path missing")

                clean_hash = hasher.calculate_file_hash(str(clean_path))
                clean_info = {
                    "width": 0,
                    "height": 0,
                    "format": cleaned_format,
                    "mode": "",
                    "file_size": clean_path.stat().st_size,
                }
                if mf.suffix.lower() != ".mp4":
                    from PIL import Image
                    with Image.open(clean_path) as cim:
                        clean_info.update({
                            "width": cim.width,
                            "height": cim.height,
                            "mode": cim.mode,
                        })

                cleaned_file_id = db.record_file(
                    run_id, "cleaned", clean_path.name, str(clean_path), clean_hash, clean_info
                )

                # Obfuscation summary
                obfuscation_log["lsb_flip_probability"] = config.get("lsb_flip_probability")
                db.record_obfuscation_summary(
                    cleaned_file_id,
                    original_file_id,
                    obfuscation_log,
                    original_info.get("format", ""),
                    cleaned_format,
                )

                db.record_action(run_id, cleaned_file_id, "process_media", {
                    "input_hash": original_hash,
                    "output_hash": clean_hash,
                    "format_change": str(original_info.get("format", "")).upper() != str(cleaned_format).upper(),
                })

                # Remove from ingest
                mf.unlink()
                db.record_action(run_id, original_file_id, "remove_from_ingest", {"ingest_path": str(mf)})

                stats["successful"] += 1
            except Exception as e:  # noqa: BLE001
                print(f"[bold red] • Error processing {escape(mf.name)}: {escape(str(e))}[/]")
                db.record_action(run_id, 0, "processing_error", {"file": str(mf), "error": str(e)})
                stats["failed"] += 1
            finally:
                progress.advance(task_id)
                progress.console.print()

    db.finish_run(run_id, stats)

    print("[bold green]=== PROCESSING COMPLETE ===[/]")
    print(f"Total files: {stats['total']}")
    print(f"Successfully processed: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    if stats["successful"] > 0:
        print(f"\nCleaned files in: {escape(str(dirs['clean']))}")
        print(f"Originals preserved in: {escape(str(dirs['originals']))}")
        print(f"Audit trail in database: {escape(str(db_path))}")


def main() -> None:
    project_root = Path(__file__).resolve().parent

    # Setup checks
    ensure_workspace(project_root)
    show_welcome_message()

    # ffmpeg upfront note
    try:
        from secure_pipeline.secure_video_processor import SecureVideoProcessor
        if not SecureVideoProcessor().ffmpeg_available():
            print("[bold yellow]Note:[/] ffmpeg not found — MP4 metadata stripping disabled.")
    except Exception:
        pass

    while True:
        print("\nOptions:")
        print("1. Configure and process media")
        print("2. Exit")
        choice = prompt("Select option (1-2): ").strip()
        if choice == "1":
            cfg = choose_configuration()
            process_batch(project_root, cfg)
        elif choice == "2":
            print("\nExiting. Stay safe.")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
