import os
import sys
from datetime import datetime
from pathlib import Path

# Add src/ to path so autodoc can import the package
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

project = "Secure Media Processing Pipeline"
author = "Secure Pipeline Team"
copyright = f"{datetime.utcnow().year}, {author}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": False,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = True

