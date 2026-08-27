#!/usr/bin/env python3
"""Launch Tolmach through this fork's protected server entry point."""

import launch


if __name__ == "__main__":
    # Reuse Tolmach's complete bootstrap (venv, dependencies, Ollama, models,
    # restart handling and browser opening). Only the server script is swapped.
    launch.SRC_DIR = launch.PROJECT_DIR / "src" / "custom"
    launch.main()
