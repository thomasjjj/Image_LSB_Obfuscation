#!/usr/bin/env python3
"""
Compatibility launcher for the interactive CLI.

Delegates to cli in the Image_LSB package so business logic stays in reusable API functions.
"""

from Image_LSB.cli import main


if __name__ == "__main__":
    main()
