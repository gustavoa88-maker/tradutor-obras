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

    # This fork is currently being validated on an 8 GB Windows machine. Keep
    # only one Ollama model resident, avoid parallel inference, unload models
    # immediately after a request, and cap the default context so the CPU/RAM
    # fallback remains usable. These values affect an Ollama server started by
    # this launcher; API-level options can still override them later if needed.
    os.environ.setdefault("OLLAMA_KEEP_ALIVE", "0")
    os.environ.setdefault("OLLAMA_MAX_LOADED_MODELS", "1")
    os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")
    os.environ.setdefault("OLLAMA_CONTEXT_LENGTH", "4096")

    # Keep the 12B translation model for the quality test, but use a small
    # independent judge instead of Tolmach's 32B default. qwen3:4b is a real
    # independent instruct model while remaining plausible on 8 GB RAM when
    # models are loaded sequentially.
    launch.MINIMUM_TRANSLATION_MODEL = "translategemma:12b"
    launch.MINIMUM_JUDGE_MODEL = "qwen3:4b"

    # Reuse Tolmach's complete bootstrap (venv, dependencies, Ollama, models,
    # restart handling and browser opening). Only the server script is swapped.
    launch.find_ollama = _find_ollama_with_current_windows_path
    launch.SRC_DIR = launch.PROJECT_DIR / "src" / "custom"
    launch.main()
