#!/usr/bin/env python3
"""Launch Tolmach through this fork's protected server entry point."""

import os
import sys
from pathlib import Path

import launch


_original_find_ollama = launch.find_ollama


def _find_ollama_with_current_windows_path():
    """Recognize both Tolmach's legacy fallback and Ollama's current installer path."""
    found = _original_find_ollama()
    if found:
        return found
    if launch.IS_WINDOWS:
        candidate = (
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs"
            / "Ollama"
            / "ollama.exe"
        )
        if candidate.exists():
            return str(candidate)
    return None


if __name__ == "__main__":
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(
            "Tradutor Obras currently requires Python 3.12 for the supported Windows setup. "
            "Run it with: py -3.12 launch_tradutor_obras.py"
        )

    # Reuse Tolmach's complete bootstrap (venv, dependencies, Ollama, models,
    # restart handling and browser opening). Only the server script is swapped.
    launch.find_ollama = _find_ollama_with_current_windows_path
    launch.SRC_DIR = launch.PROJECT_DIR / "src" / "custom"
    launch.main()
