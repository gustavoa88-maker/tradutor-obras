"""Runtime integration for mechanically protected proper-name nuclei.

Tolmach's translation pipeline is intentionally left upstream-shaped.  This
module installs three narrow wrappers around the places where translated prose
can be generated or rewritten:

* Stage 1 source text is shielded before the model sees it and restored after;
* Review Desk alternatives get the same shielding;
* Stage 2 is not allowed to keep a refinement that changes a protected name.

Keeping the integration here makes future upstream synchronisation much less
conflict-prone than scattering custom edits through translator.py.
"""

from __future__ import annotations

from functools import wraps
from typing import Any


_INSTALLED_ATTR = "_tolmach_proper_name_protection_installed"


def _violation_summary(violations: list[dict]) -> str:
    return ", ".join(
        f"{item.get('source', '?')} ({item.get('actual_count', 0)}/"
        f"{item.get('expected_count', 1)})"
        for item in violations
    )


def install(core: Any) -> None:
    """Install proper-name protection on ``core.BookTranslator`` once."""
    cls = core.BookTranslator
    if getattr(cls, _INSTALLED_ATTR, False):
        return

    original_stage1 = cls.stage1_primary_translation
    original_candidate = cls.generate_translation_candidate
    original_stage2 = cls.stage2_reflection_improvement

    @wraps(original_stage1)
    def protected_stage1(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        previous_chunk: str = "",
        genre: str = "unknown",
        terminology_context: str = "",
    ):
        original_text = text
        protected_text, markers = self.terminology.protect_preserved_terms(text)
        translated, warning = original_stage1(
            self,
            protected_text,
            source_lang,
            target_lang,
            previous_chunk=previous_chunk,
            genre=genre,
            terminology_context=terminology_context,
        )
        restored, marker_violations = self.terminology.restore_preserved_terms(
            translated,
            markers,
        )
        if marker_violations:
            detail = _violation_summary(marker_violations)
            core.logger.translation_logger.warning(
                "Stage 1 rejected a chunk because protected-name markers were altered: %s",
                detail,
            )
            return (
                original_text,
                "The model altered a protected proper-name marker "
                f"({detail}) — kept the original chunk untranslated so no name was corrupted.",
            )

        preserve_violations = self.terminology.preserve_occurrence_violations(
            original_text,
            restored,
        )
        if preserve_violations:
            detail = _violation_summary(preserve_violations)
            core.logger.translation_logger.warning(
                "Stage 1 rejected a chunk because protected-name counts changed: %s",
                detail,
            )
            return (
                original_text,
                "The model changed a protected proper name "
                f"({detail}) — kept the original chunk untranslated so no name was corrupted.",
            )
        return restored, warning

    @wraps(original_candidate)
    def protected_candidate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        *,
        previous_chunk: str = "",
        genre: str = "unknown",
        terminology_context: str = "",
        temperature: float = 0.6,
    ):
        original_text = text
        protected_text, markers = self.terminology.protect_preserved_terms(text)
        candidate, warning = original_candidate(
            self,
            protected_text,
            source_lang,
            target_lang,
            previous_chunk=previous_chunk,
            genre=genre,
            terminology_context=terminology_context,
            temperature=temperature,
        )
        if candidate is None:
            return None, warning

        restored, marker_violations = self.terminology.restore_preserved_terms(
            candidate,
            markers,
        )
        preserve_violations = self.terminology.preserve_occurrence_violations(
            original_text,
            restored,
        )
        violations = marker_violations or preserve_violations
        if violations:
            detail = _violation_summary(violations)
            core.logger.translation_logger.warning(
                "Review candidate discarded because it damaged a protected name: %s",
                detail,
            )
            return None, (
                "A generated candidate altered a protected proper name "
                f"({detail}) and was discarded."
            )
        return restored, warning

    @wraps(original_stage2)
    def protected_stage2(
        self,
        original_text: str,
        draft_translation: str,
        source_lang: str,
        target_lang: str,
        genre: str = "unknown",
        terminology_context: str = "",
        terminology_violations=None,
    ):
        candidate, warning, details = original_stage2(
            self,
            original_text,
            draft_translation,
            source_lang,
            target_lang,
            genre=genre,
            terminology_context=terminology_context,
            terminology_violations=terminology_violations,
        )
        violations = self.terminology.preserve_occurrence_violations(
            original_text,
            candidate,
        )
        if not violations:
            return candidate, warning, details

        detail = _violation_summary(violations)
        details = dict(details or {})
        details["preserve_rejected"] = violations
        core.logger.translation_logger.warning(
            "Stage 2 rejected a refinement that damaged protected names: %s",
            detail,
        )
        protection_warning = (
            "Refinement changed a protected proper name "
            f"({detail}) — kept the Stage 1 draft for this chunk."
        )
        return draft_translation, warning or protection_warning, details

    cls.stage1_primary_translation = protected_stage1
    cls.generate_translation_candidate = protected_candidate
    cls.stage2_reflection_improvement = protected_stage2
    setattr(cls, _INSTALLED_ATTR, True)
