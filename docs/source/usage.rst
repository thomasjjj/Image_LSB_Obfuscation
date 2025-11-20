Usage Guide
===========

Install
-------

.. code-block:: bash

   # development
   pip install -r requirements-dev.txt

   # or as a package
   pip install .

CLI
---

Run the CLI to process media from the ingest folder and write to clean/ with originals preserved in originals/ and an audit DB:

.. code-block:: bash

   image-lsb

   # or
   python main.py

Library
-------

.. code-block:: python

   from Image_LSB import image_clean, video_clean
   from PIL import Image

   # Clean an image on disk
   img, log, path = image_clean(
       "ingest/photo.jpg",
       lsb_flip_probability=0.2,
       obfuscation_passes=3,
       add_noise=True,
       output_format="JPEG",
       jpeg_quality=85,
       output_dir="clean",
   )

   # Clean an in-memory image
   im = Image.open("photo.png")
   clean_im, log, path = image_clean(im)

   # Strip metadata from a video (requires ffmpeg)
   out_path, details = video_clean("clips/source.mp4", output_dir="clean")

Configuration
-------------

Environment variables can override directory names and defaults:

- ``PIPELINE_INGEST_DIR`` (default: ``ingest``)
- ``PIPELINE_CLEAN_DIR`` (``clean``)
- ``PIPELINE_ORIGINALS_DIR`` (``originals``)
- ``PIPELINE_DB_DIR`` (``db``)
- ``PIPELINE_LOG_DIR`` (``logs``)
- ``PIPELINE_DB_FILENAME`` (``processing.db``)
- ``PIPELINE_DEFAULT_SECURITY_LEVEL`` (1–4)

Optional fine-tuning used by the CLI defaults:

- ``PIPELINE_LSB_FLIP_PROBABILITY``
- ``PIPELINE_OBFUSCATION_PASSES``
- ``PIPELINE_ADD_NOISE``
- ``PIPELINE_OUTPUT_FORMAT``
- ``PIPELINE_JPEG_QUALITY``
