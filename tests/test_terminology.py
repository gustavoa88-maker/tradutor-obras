import pytest

from translator import GlossaryTerm, TerminologyManager


def test_parses_arrow_and_tsv_formats():
    manager = TerminologyManager.from_text(
        """
        Mr. Darcy => мистер Дарси | exact
        machine learning\tmaschinelles Lernen\tinflectable
        Home => Heimat
        Wang Lin => Wang Lin | preserve
        """
    )

    assert manager.terms == [
        GlossaryTerm("Mr. Darcy", "мистер Дарси", "exact"),
        GlossaryTerm("machine learning", "maschinelles Lernen", "inflectable"),
        GlossaryTerm("Home", "Heimat", "inflectable"),
        GlossaryTerm("Wang Lin", "Wang Lin", "preserve"),
    ]


def test_omitted_mode_defaults_to_inflectable_for_arrow_and_tsv_formats():
    manager = TerminologyManager.from_text(
        "home => дом\nmachine learning\tмашинное обучение"
    )

    assert manager.terms == [
        GlossaryTerm("home", "дом", "inflectable"),
        GlossaryTerm("machine learning", "машинное обучение", "inflectable"),
    ]


def test_preserve_requires_identical_source_and_target():
    with pytest.raises(ValueError, match="preserve requires identical source and target"):
        TerminologyManager.from_text("Wang Lin => Ван Линь | preserve")


def test_relevance_is_case_insensitive_and_supports_cjk():
    manager = TerminologyManager.from_text(
        """
        ALICE => Алиса | exact
        人工知能 => artificial intelligence | exact
        """
    )

    assert [term.source for term in manager.relevant_terms("Alice met Bob.")] == [
        "ALICE"
    ]
    assert [term.source for term in manager.relevant_terms("人工知能の研究")] == [
        "人工知能"
    ]


def test_preserve_relevance_is_case_sensitive_for_contextual_names():
    manager = TerminologyManager.from_text("Host => Host | preserve")

    assert [term.source for term in manager.relevant_terms("The Host arrived.")] == [
        "Host"
    ]
    assert manager.relevant_terms("The host welcomed the guests.") == []


def test_preserve_protects_only_proper_name_nuclei_and_longest_overlap():
    manager = TerminologyManager.from_text(
        """
        Host => Host | preserve
        Wang Lin => Wang Lin | preserve
        Wang => Wang | preserve
        Ji => Ji | preserve
        """
    )
    source = (
        "The Host met the host. Fellow Daoist Wang greeted Wang Lin "
        "before entering the Ji Realm."
    )

    protected, markers = manager.protect_preserved_terms(source)

    assert [marker["source"] for marker in markers] == [
        "Host",
        "Wang",
        "Wang Lin",
        "Ji",
    ]
    assert "the host" in protected
    assert "Fellow Daoist " in protected
    assert " Realm" in protected
    assert "Wang Lin" not in protected
    assert all(protected.count(marker["placeholder"]) == 1 for marker in markers)


def test_preserve_markers_can_move_with_target_grammar_and_restore_exact_names():
    manager = TerminologyManager.from_text(
        """
        Wang => Wang | preserve
        Ji => Ji | preserve
        """
    )
    source = "Fellow Daoist Wang entered the Ji Realm."
    _, markers = manager.protect_preserved_terms(source)

    translated_with_markers = (
        f"Companheiro Daoista {markers[0]['placeholder']} entrou no "
        f"Reino {markers[1]['placeholder']}."
    )
    restored, violations = manager.restore_preserved_terms(
        translated_with_markers,
        markers,
    )

    assert restored == "Companheiro Daoista Wang entrou no Reino Ji."
    assert violations == []


def test_restore_reports_missing_or_duplicated_preserve_markers():
    manager = TerminologyManager.from_text(
        "Wang => Wang | preserve\nJi => Ji | preserve"
    )
    _, markers = manager.protect_preserved_terms("Wang entered the Ji Realm.")

    damaged = markers[0]["placeholder"] * 2
    restored, violations = manager.restore_preserved_terms(damaged, markers)

    assert restored == "WangWang"
    assert violations == [
        {"source": "Wang", "expected_count": 1, "actual_count": 2},
        {"source": "Ji", "expected_count": 1, "actual_count": 0},
    ]


def test_final_preserve_validation_checks_exact_occurrence_counts():
    manager = TerminologyManager.from_text(
        "Wang Lin => Wang Lin | preserve\nHost => Host | preserve"
    )
    source = "Wang Lin joined the Host. Wang Lin returned."

    assert manager.preserve_occurrence_violations(
        source,
        "Wang Lin entrou para o Host. Wang Lin voltou.",
    ) == []
    assert manager.preserve_occurrence_violations(
        source,
        "Wang Lin entrou para o Host.",
    ) == [
        {"source": "Wang Lin", "expected_count": 2, "actual_count": 1}
    ]


def test_exact_violations_only_check_relevant_exact_terms():
    manager = TerminologyManager.from_text(
        """
        garden => сад | exact
        house => дом | preferred
        absent => отсутствует | exact
        """
    )

    assert manager.exact_violations("The garden and house.", "Сад и жилище.") == []
    assert manager.exact_violations("The garden and house.", "Двор и жилище.") == [
        {"source": "garden", "required_target": "сад"}
    ]


def test_exact_terms_replace_only_literal_source_leaks():
    manager = TerminologyManager.from_text(
        "Dursley => Дурсль | exact\nHome => дом | inflectable"
    )

    translated, replacements = manager.enforce_exact_source_forms(
        "Dursley arrived. The Dursleys stayed. Home remained untranslated."
    )

    assert translated == "Дурсль arrived. The Dursleys stayed. Home remained untranslated."
    assert replacements == [{"source": "Dursley", "target": "Дурсль", "count": 1}]


def test_exact_source_replacement_is_case_insensitive_but_respects_word_boundaries():
    manager = TerminologyManager.from_text("garden => сад | exact")

    translated, replacements = manager.enforce_exact_source_forms(
        "GARDEN, garden; gardener; gardens."
    )

    assert translated == "сад, сад; gardener; gardens."
    assert replacements == [{"source": "garden", "target": "сад", "count": 2}]


def test_fingerprint_is_stable_but_changes_with_constraints():
    first = TerminologyManager.from_text(
        "cat => кот | exact\ndog => пёс | preferred"
    )
    reordered = TerminologyManager.from_text(
        "dog => пёс | preferred\ncat => кот | exact"
    )
    changed = TerminologyManager.from_text(
        "cat => кошка | exact\ndog => пёс | preferred"
    )

    assert first.fingerprint() == reordered.fingerprint()
    assert first.fingerprint() != changed.fingerprint()
