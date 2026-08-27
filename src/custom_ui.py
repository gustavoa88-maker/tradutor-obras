"""Small runtime UI overlay for Tradutor Obras.

The upstream Tolmach workbench remains untouched on disk.  This module changes
only the glossary help/validation strings that this fork needs for the
``preserve`` mode when the home page is served.  Keeping the delta here avoids
a large, conflict-prone fork of ``src/static/index.html``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


_MODE_SET = "const GLOSSARY_VALID_MODES = new Set(['exact', 'inflectable', 'preferred']);"
_MODE_SET_WITH_PRESERVE = (
    "const GLOSSARY_VALID_MODES = new Set(['exact', 'inflectable', 'preferred', 'preserve']);"
)

_MODE_ERROR = (
    "if (!reason && !GLOSSARY_VALID_MODES.has(mode)) reason = "
    "'mode must be exact, inflectable, or preferred';"
)
_MODE_ERROR_WITH_PRESERVE = (
    "if (!reason && !GLOSSARY_VALID_MODES.has(mode)) reason = "
    "'mode must be exact, inflectable, preferred, or preserve';\n"
    "                if (!reason && mode === 'preserve' && source !== target) "
    "reason = 'preserve requires identical source and target';"
)

_HELP_ANCHOR = (
    '<div class="guide-mode"><span class="guide-mode-label">preferred</span>'
    '<span class="guide-mode-description">Use this translation where it fits, '
    'otherwise the app translates freely.</span></div>'
)
_HELP_WITH_PRESERVE = _HELP_ANCHOR + (
    '\n                        <div class="guide-mode"><span class="guide-mode-label">preserve</span>'
    '<span class="guide-mode-description">Keep this proper-name spelling exactly as written in the source. '
    'Source and target must be identical.</span></div>'
)


def _replace_once(html: str, old: str, new: str, label: str) -> str:
    count = html.count(old)
    if count != 1:
        raise RuntimeError(
            f"Could not apply Tradutor Obras UI overlay for {label}: "
            f"expected one upstream anchor, found {count}."
        )
    return html.replace(old, new, 1)


def transform_index_html(html: str) -> str:
    """Return the Tolmach home page with ``preserve`` exposed safely."""
    html = _replace_once(html, _MODE_SET, _MODE_SET_WITH_PRESERVE, "valid modes")
    html = _replace_once(
        html,
        _MODE_ERROR,
        _MODE_ERROR_WITH_PRESERVE,
        "browser glossary validation",
    )
    html = _replace_once(html, _HELP_ANCHOR, _HELP_WITH_PRESERVE, "glossary help")
    return html


def install(core: Any) -> None:
    """Replace only the Flask home-page view with the transformed upstream HTML."""
    view_name = "serve_frontend"
    if getattr(core.app, "_tradutor_obras_ui_overlay_installed", False):
        return
    if view_name not in core.app.view_functions:
        raise RuntimeError("Tolmach home-page view was not found; UI overlay cannot be installed.")

    index_path = Path(core.STATIC_FOLDER) / "index.html"

    def serve_frontend_overlay():
        html = index_path.read_text(encoding="utf-8")
        response = core.Response(transform_index_html(html), mimetype="text/html")
        response.headers["Cache-Control"] = "no-store"
        return response

    core.app.view_functions[view_name] = serve_frontend_overlay
    setattr(core.app, "_tradutor_obras_ui_overlay_installed", True)
