#!/usr/bin/env python3
"""Fast local smoke test for Tradutor Obras proper-name preservation.

Uses only the Python standard library plus this repository's own modules.  It
does not start Flask, Ollama, or a translation model.
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from custom_ui import transform_index_html  # noqa: E402
from terminology import TerminologyManager  # noqa: E402


def main() -> None:
    glossary = """
Wang => Wang | preserve
Wang Lin => Wang Lin | preserve
Ji => Ji | preserve
Host => Host | preserve
"""
    manager = TerminologyManager.from_text(glossary)
    source = (
        "The Host greeted the host. Fellow Daoist Wang spoke with Wang Lin "
        "before entering the Ji Realm."
    )

    protected, markers = manager.protect_preserved_terms(source)
    assert [marker["source"] for marker in markers] == ["Host", "Wang", "Wang Lin", "Ji"]
    assert "the host" in protected
    assert "Fellow Daoist " in protected
    assert " Realm" in protected
    assert "Wang Lin" not in protected

    simulated_translation = (
        f"O {markers[0]['placeholder']} cumprimentou o anfitrião. "
        f"Companheiro Daoista {markers[1]['placeholder']} falou com "
        f"{markers[2]['placeholder']} antes de entrar no Reino "
        f"{markers[3]['placeholder']}."
    )
    restored, marker_violations = manager.restore_preserved_terms(
        simulated_translation,
        markers,
    )
    assert marker_violations == []
    assert restored == (
        "O Host cumprimentou o anfitrião. Companheiro Daoista Wang falou com "
        "Wang Lin antes de entrar no Reino Ji."
    )
    assert manager.preserve_occurrence_violations(source, restored) == []

    index_html = (SRC / "static" / "index.html").read_text(encoding="utf-8")
    transformed = transform_index_html(index_html)
    assert "new Set(['exact', 'inflectable', 'preferred', 'preserve'])" in transformed
    assert "preserve requires identical source and target" in transformed

    print("OK: preserve core")
    print("OK: longest-name overlap")
    print("OK: case-sensitive Host/host")
    print("OK: exact occurrence restoration")
    print("OK: browser glossary validation overlay")
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
