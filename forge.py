#!/usr/bin/env python3
"""Forge CLI entry point."""

import sys
from pathlib import Path

# Ensure forge package can be imported directly
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from forge.cli import app, cli_main

if __name__ == "__main__":
    cli_main()
