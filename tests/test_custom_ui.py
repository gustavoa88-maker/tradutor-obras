from pathlib import Path

from custom_ui import transform_index_html


INDEX_HTML = Path(__file__).resolve().parents[1] / "src" / "static" / "index.html"


def test_runtime_ui_overlay_exposes_preserve_mode_without_editing_upstream_html():
    original = INDEX_HTML.read_text(encoding="utf-8")

    assert "'preserve'" not in original.split("GLOSSARY_VALID_MODES", 1)[1].split(";", 1)[0]

    transformed = transform_index_html(original)

    assert "new Set(['exact', 'inflectable', 'preferred', 'preserve'])" in transformed
    assert "mode must be exact, inflectable, preferred, or preserve" in transformed
    assert "mode === 'preserve' && source !== target" in transformed
    assert "preserve requires identical source and target" in transformed
    assert '<span class="guide-mode-label">preserve</span>' in transformed
    assert "Keep this proper-name spelling exactly as written in the source." in transformed


def test_runtime_ui_overlay_fails_loudly_if_upstream_contract_changes():
    try:
        transform_index_html("<html>upstream changed</html>")
    except RuntimeError as error:
        assert "expected one upstream anchor" in str(error)
    else:
        raise AssertionError("overlay should fail instead of silently skipping an upstream change")
