#!/usr/bin/env python3
"""Tradutor Obras server entry point.

Imports the upstream-shaped Tolmach server, installs this fork's proper-name
protection and small UI overlay, then starts the same Flask application.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
from pathlib import Path

# This file lives one directory below src/. Put src/ first so ``translator``
# resolves to Tolmach's original server module rather than to this wrapper.
SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

import translator as core  # noqa: E402
from custom_ui import install as install_custom_ui  # noqa: E402
from proper_name_protection import install as install_proper_name_protection  # noqa: E402

install_proper_name_protection(core)
install_custom_ui(core)


def main() -> None:
    threading.Thread(target=core.cleanup_old_data, daemon=True).start()

    def signal_handler(signum, frame):
        print("Shutting down gracefully...")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    core.print_terminal_banner()
    core.setup_access_log()
    core.app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5001)),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )


if __name__ == "__main__":
    main()
