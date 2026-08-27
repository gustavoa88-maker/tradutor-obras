#!/usr/bin/env python3
"""Launch Tolmach through this fork's protected server entry point."""

import sys

import launch


if __name__ == "__main__":
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(
            "Tradutor Obras currently requires Python 3.12 for the supported Windows setup. "
            "Run it with: py -3.12 launch_tradutor_obras.py"
        )

    # Reuse Tolmach's complete bootstrap (venv, dependencies, Ollama, models,
    # restart handling and browser opening). Only the server script is swapped.
    launch.SRC_DIR = launch.PROJECT_DIR / "src" / "custom"
    launch.main()
