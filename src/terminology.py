"""Per-book terminology constraints: the agreed rendering of recurring terms,
plus deterministic protection for proper names that must survive translation.

Language-neutral by design — it knows nothing about which languages a run is
between, only about the terms it was given.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TypedDict

import prompts


class ExactReplacement(TypedDict):
    """One enforced ``exact`` rule: the term, and how often it was rewritten."""

    source: str
    target: str
    count: int


class PreserveMarker(TypedDict):
    """One source occurrence hidden from the model behind a unique marker."""

    placeholder: str
    source: str


class PreserveViolation(TypedDict):
    """A preservation invariant that was not satisfied."""

    source: str
    expected_count: int
    actual_count: int


@dataclass(frozen=True)
class GlossaryTerm:
    source: str
    target: str
    mode: str = "inflectable"


class TerminologyManager:
    """Language-neutral, per-book terminology constraints."""

    VALID_MODES = {"exact", "inflectable", "preferred", "preserve"}
    MAX_TERMS = 500
    MAX_TERM_LENGTH = 200

    def __init__(self, terms: Optional[List[GlossaryTerm]] = None):
        deduplicated = {}
        for term in terms or []:
            # Preserve is intentionally case-sensitive at match time (Host and
            # host can mean different things), but glossary identity remains
            # case-insensitive so two rules cannot silently fight each other.
            deduplicated[term.source.casefold()] = term
        self.terms = list(deduplicated.values())

    @classmethod
    def from_text(cls, glossary_text: str):
        """Parse `source => target | mode` or TSV lines; mode defaults to inflectable."""
        terms = []
        for line_number, raw_line in enumerate(glossary_text.splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            mode = "inflectable"
            if "\t" in line:
                parts = [part.strip() for part in line.split("\t")]
                if len(parts) not in (2, 3):
                    raise ValueError(
                        f"Glossary line {line_number}: use source<TAB>target<TAB>mode"
                    )
                source, target = parts[:2]
                if len(parts) == 3:
                    mode = parts[2].lower()
            else:
                separator = "=>" if "=>" in line else "=" if "=" in line else None
                if not separator:
                    raise ValueError(
                        f"Glossary line {line_number}: use source => target | mode"
                    )
                source, remainder = [part.strip() for part in line.split(separator, 1)]
                if "|" in remainder:
                    target, mode = [part.strip() for part in remainder.rsplit("|", 1)]
                    mode = mode.lower()
                else:
                    target = remainder.strip()

            if not source or not target:
                raise ValueError(f"Glossary line {line_number}: both terms are required")
            if len(source) > cls.MAX_TERM_LENGTH or len(target) > cls.MAX_TERM_LENGTH:
                raise ValueError(
                    f"Glossary line {line_number}: a term exceeds {cls.MAX_TERM_LENGTH} characters"
                )
            if mode not in cls.VALID_MODES:
                raise ValueError(
                    f"Glossary line {line_number}: mode must be exact, inflectable, preferred, or preserve"
                )
            if mode == "preserve" and source != target:
                raise ValueError(
                    f"Glossary line {line_number}: preserve requires identical source and target"
                )
            terms.append(GlossaryTerm(source=source, target=target, mode=mode))

        if len(terms) > cls.MAX_TERMS:
            raise ValueError(f"Glossary supports at most {cls.MAX_TERMS} terms")
        return cls(terms)

    @staticmethod
    def _literal_pattern(source: str, *, ignore_case: bool = False) -> re.Pattern:
        """Match a literal term without swallowing it from a longer Latin word.

        ASCII boundaries are deliberate. They protect English/romanized names
        such as ``Wang`` from matching ``Wangly`` while still allowing exact
        CJK strings to match when adjacent to other CJK characters.
        """
        left = r"(?<![A-Za-z0-9_])" if source and re.match(r"[A-Za-z0-9_]", source[0]) else ""
        right = r"(?![A-Za-z0-9_])" if source and re.match(r"[A-Za-z0-9_]", source[-1]) else ""
        flags = re.IGNORECASE if ignore_case else 0
        return re.compile(f"{left}{re.escape(source)}{right}", flags)

    def relevant_terms(self, source_text: str) -> List[GlossaryTerm]:
        folded_text = source_text.casefold()
        relevant = []
        for term in self.terms:
            if term.mode == "preserve":
                if self._literal_pattern(term.source).search(source_text):
                    relevant.append(term)
            elif term.source.casefold() in folded_text:
                relevant.append(term)
        return relevant

    def prompt_context(self, source_text: str) -> str:
        relevant = self.relevant_terms(source_text)
        if not relevant:
            return ""

        lines = [
            prompts.render(
                "shared/terminology", "entry",
                source=term.source,
                target=term.target,
                rule=prompts.render("shared/terminology", f"mode_{term.mode}"),
            )
            for term in relevant
        ]
        # The two blank lines belong to the prompt this block is spliced into,
        # not to the block, so they are added here rather than in the file.
        return "\n\n" + prompts.render(
            "shared/terminology", entries="\n".join(lines),
        )

    def protect_preserved_terms(self, source_text: str) -> Tuple[str, List[PreserveMarker]]:
        """Replace every ``preserve`` occurrence with a unique opaque marker.

        Matching is case-sensitive by design. A rule for ``Host`` therefore
        protects the formal name while ordinary ``host`` remains translatable.
        Longer names win over shorter overlapping names, so ``Wang Lin`` is
        protected as one unit even when ``Wang`` is also registered.
        """
        preserve_terms = [term for term in self.terms if term.mode == "preserve"]
        if not preserve_terms or not source_text:
            return source_text, []

        # One combined regex prevents a shorter term from seeing text that has
        # already been replaced by a marker. Sorting makes the longest overlap
        # win at the same source position.
        ordered = sorted(preserve_terms, key=lambda term: len(term.source), reverse=True)
        alternatives = []
        by_group = {}
        for index, term in enumerate(ordered):
            group = f"term_{index}"
            literal = self._literal_pattern(term.source).pattern
            alternatives.append(f"(?P<{group}>{literal})")
            by_group[group] = term
        combined = re.compile("|".join(alternatives))

        nonce = hashlib.sha256(
            (self.fingerprint() + "\0" + source_text).encode("utf-8")
        ).hexdigest()[:10]
        markers: List[PreserveMarker] = []
        used_placeholders = set()

        def replacement(match: re.Match) -> str:
            term = by_group[match.lastgroup]
            marker_index = len(markers)
            placeholder = f"⟦TOLMACH_KEEP_{nonce}_{marker_index:04d}⟧"
            while placeholder in source_text or placeholder in used_placeholders:
                marker_index += 1
                placeholder = f"⟦TOLMACH_KEEP_{nonce}_{marker_index:04d}⟧"
            used_placeholders.add(placeholder)
            markers.append({"placeholder": placeholder, "source": term.source})
            return placeholder

        return combined.sub(replacement, source_text), markers

    @staticmethod
    def restore_preserved_terms(
        translated_text: str,
        markers: List[PreserveMarker],
    ) -> Tuple[str, List[PreserveViolation]]:
        """Restore markers and report any marker that was lost or duplicated."""
        result = translated_text
        violations: List[PreserveViolation] = []
        for marker in markers:
            placeholder = marker["placeholder"]
            count = result.count(placeholder)
            if count != 1:
                violations.append({
                    "source": marker["source"],
                    "expected_count": 1,
                    "actual_count": count,
                })
            if count:
                result = result.replace(placeholder, marker["source"])
        return result, violations

    def preserve_occurrence_violations(
        self,
        source_text: str,
        translated_text: str,
    ) -> List[PreserveViolation]:
        """Verify that final output kept every protected spelling and count."""
        violations: List[PreserveViolation] = []
        for term in self.terms:
            if term.mode != "preserve":
                continue
            pattern = self._literal_pattern(term.source)
            expected = len(pattern.findall(source_text))
            if not expected:
                continue
            actual = len(pattern.findall(translated_text))
            if actual != expected:
                violations.append({
                    "source": term.source,
                    "expected_count": expected,
                    "actual_count": actual,
                })
        return violations

    def exact_violations(self, source_text: str, translated_text: str) -> List[Dict]:
        """Return every hard terminology violation used by existing QA callers.

        The method keeps its historical name because the translation pipeline,
        review desk, and quality checks already call it. ``preserve`` is also a
        hard invariant now: every exact source spelling must survive with the
        same occurrence count, so those failures are surfaced through the same
        path instead of requiring every caller to learn a second API.
        """
        translated_folded = translated_text.casefold()
        violations: List[Dict] = [
            {"source": term.source, "required_target": term.target, "mode": "exact"}
            for term in self.relevant_terms(source_text)
            if term.mode == "exact" and term.target.casefold() not in translated_folded
        ]
        violations.extend(
            {
                "source": item["source"],
                "required_target": item["source"],
                "mode": "preserve",
                "expected_count": item["expected_count"],
                "actual_count": item["actual_count"],
            }
            for item in self.preserve_occurrence_violations(source_text, translated_text)
        )
        return violations

    def enforce_exact_source_forms(self, translated_text: str) -> Tuple[str, List[ExactReplacement]]:
        """Replace an exact term only when the model leaked its source form.

        A glossary is still provided to the model as translation context: it
        remains the only safe way to choose a rendering that is absent from
        the output. But an ``exact`` rule has one deterministic case we can
        honour without guessing — the model translated the surrounding prose
        and left the literal source term unchanged. Fix that case here, both
        for fresh generations and cached chunks. ``inflectable``, ``preferred``
        and ``preserve`` terms are intentionally never rewritten this way.
        """
        replacements: List[ExactReplacement] = []
        result = translated_text
        for term in self.terms:
            if term.mode != "exact" or term.source.casefold() == term.target.casefold():
                continue
            # Do not turn a source substring inside a longer word into a
            # glossary term.
            pattern = self._literal_pattern(term.source, ignore_case=True)
            result, count = pattern.subn(term.target, result)
            if count:
                replacements.append({
                    "source": term.source,
                    "target": term.target,
                    "count": count,
                })
        return result, replacements

    def fingerprint(self) -> str:
        canonical = sorted(
            (term.source.casefold(), term.target, term.mode) for term in self.terms
        )
        payload = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
