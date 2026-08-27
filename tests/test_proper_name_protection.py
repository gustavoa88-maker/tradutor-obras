import re
from types import SimpleNamespace

from proper_name_protection import install
from terminology import TerminologyManager


class _LogSink:
    def __init__(self):
        self.messages = []

    def warning(self, message, *args):
        self.messages.append(message % args if args else message)


def _core(stage1, candidate=None, stage2=None):
    class FakeTranslator:
        stage1_primary_translation = stage1
        generate_translation_candidate = candidate or stage1
        stage2_reflection_improvement = stage2 or (
            lambda self, original_text, draft_translation, source_lang, target_lang,
            genre="unknown", terminology_context="", terminology_violations=None:
            (draft_translation, None, {})
        )

        def __init__(self, terminology):
            self.terminology = terminology

    sink = _LogSink()
    core = SimpleNamespace(
        BookTranslator=FakeTranslator,
        logger=SimpleNamespace(translation_logger=sink),
    )
    install(core)
    return core, sink


def test_stage1_shields_only_name_nuclei_and_restores_target_grammar():
    def stage1(self, text, source_lang, target_lang, **kwargs):
        markers = re.findall(r"⟦TOLMACH_KEEP_[^⟧]+⟧", text)
        assert len(markers) == 2
        assert "Wang" not in text
        assert "Ji" not in text
        assert "Fellow Daoist" in text
        assert "Realm" in text
        context = kwargs["terminology_context"]
        assert "Copy every such marker exactly once" in context
        assert "Senior Brother => Irmão Mais Velho" in context
        return f"Companheiro Daoista {markers[0]} entrou no Reino {markers[1]}.", None

    terminology = TerminologyManager.from_text(
        "Wang => Wang | preserve\nJi => Ji | preserve"
    )
    core, _ = _core(stage1)
    translator = core.BookTranslator(terminology)

    translated, warning = translator.stage1_primary_translation(
        "Fellow Daoist Wang entered the Ji Realm.",
        "en",
        "pt_BR",
    )

    assert translated == "Companheiro Daoista Wang entrou no Reino Ji."
    assert warning is None


def test_non_ptbr_target_does_not_receive_ptbr_honorific_rules():
    def stage1(self, text, source_lang, target_lang, **kwargs):
        assert "Senior Brother => Irmão Mais Velho" not in kwargs["terminology_context"]
        return text, None

    terminology = TerminologyManager()
    core, _ = _core(stage1)
    translator = core.BookTranslator(terminology)

    translated, warning = translator.stage1_primary_translation(
        "Senior Brother entered the hall.",
        "en",
        "es",
    )

    assert translated == "Senior Brother entered the hall."
    assert warning is None


def test_stage1_never_accepts_a_mangled_protected_marker():
    def stage1(self, text, source_lang, target_lang, **kwargs):
        marker = re.search(r"⟦TOLMACH_KEEP_[^⟧]+⟧", text).group(0)
        return text.replace(marker, "Nome Traduzido"), None

    source = "Wang entered the city."
    terminology = TerminologyManager.from_text("Wang => Wang | preserve")
    core, sink = _core(stage1)
    translator = core.BookTranslator(terminology)

    translated, warning = translator.stage1_primary_translation(
        source,
        "en",
        "pt_BR",
    )

    assert translated == source
    assert "protected proper-name marker" in warning
    assert sink.messages


def test_stage2_rejects_a_refinement_that_changes_a_protected_name():
    def stage1(self, text, source_lang, target_lang, **kwargs):
        return text, None

    def stage2(
        self,
        original_text,
        draft_translation,
        source_lang,
        target_lang,
        **kwargs,
    ):
        return draft_translation.replace("Wang", "Vangue"), None, {"errors_applied": 1}

    terminology = TerminologyManager.from_text("Wang => Wang | preserve")
    core, sink = _core(stage1, stage2=stage2)
    translator = core.BookTranslator(terminology)

    final, warning, details = translator.stage2_reflection_improvement(
        "Wang entered the city.",
        "Wang entrou na cidade.",
        "en",
        "pt_BR",
    )

    assert final == "Wang entrou na cidade."
    assert "kept the Stage 1 draft" in warning
    assert details["preserve_rejected"] == [
        {"source": "Wang", "expected_count": 1, "actual_count": 0}
    ]
    assert sink.messages


def test_review_candidate_is_discarded_if_it_damages_a_name():
    def stage1(self, text, source_lang, target_lang, **kwargs):
        return text, None

    def candidate(self, text, source_lang, target_lang, **kwargs):
        marker = re.search(r"⟦TOLMACH_KEEP_[^⟧]+⟧", text).group(0)
        return text.replace(marker, "William"), None

    terminology = TerminologyManager.from_text("Wang => Wang | preserve")
    core, _ = _core(stage1, candidate=candidate)
    translator = core.BookTranslator(terminology)

    translated, warning = translator.generate_translation_candidate(
        "Wang entered the city.",
        "en",
        "pt_BR",
    )

    assert translated is None
    assert "discarded" in warning
