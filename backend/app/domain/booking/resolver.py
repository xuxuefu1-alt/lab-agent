from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.model.laboratory import Laboratory


def normalize_entity_text(value: str) -> str:
    return re.sub(r"[\s,，。.!！？?：:、]", "", value or "").casefold()


@dataclass(frozen=True)
class LaboratoryResolution:
    laboratory: Laboratory | None
    ambiguous: bool
    candidates: tuple[str, ...]
    method: str
    confidence: float


def _score_location_match(query: str, laboratory: Laboratory) -> int:
    location = normalize_entity_text(laboratory.location or "")
    if location and location in query and any(word in query for word in ("实验室", "实验")):
        return 80
    return 0


def resolve_laboratory(db: Session, text: str) -> LaboratoryResolution:
    query = normalize_entity_text(text)
    laboratories = (
        db.query(Laboratory)
        .filter(Laboratory.status == 1)
        .order_by(Laboratory.id)
        .all()
    )
    if not query or not laboratories:
        return LaboratoryResolution(None, False, (), "none", 0.0)

    normalized_names = [(item, normalize_entity_text(item.name or "")) for item in laboratories]

    # Full-name matching is authoritative. A shorter name must not become
    # ambiguous just because another laboratory contains the same words.
    exact = [
        (item, name)
        for item, name in normalized_names
        if name and (name == query or name in query)
    ]
    if exact:
        longest_length = max(len(name) for _, name in exact)
        longest = [item for item, name in exact if len(name) == longest_length]
        if len(longest) == 1:
            return LaboratoryResolution(longest[0], False, (), "exact_name", 1.0)
        return LaboratoryResolution(
            None,
            True,
            tuple(item.name for item in longest),
            "exact_name_ambiguous",
            0.99,
        )

    stem_matches: list[tuple[Laboratory, int]] = []
    for item, name in normalized_names:
        stem = name
        for suffix in ("实验室", "实验"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        if len(stem) >= 2 and stem in query:
            stem_matches.append((item, 0.95))
    if stem_matches:
        best_score = max(score for _, score in stem_matches)
        best = [item for item, score in stem_matches if score == best_score]
        if len(best) == 1:
            return LaboratoryResolution(best[0], False, (), "name_stem", best_score)
        return LaboratoryResolution(None, True, tuple(item.name for item in best), "name_stem_ambiguous", best_score)

    location_matches = [
        (item, _score_location_match(query, item))
        for item in laboratories
    ]
    location_matches = [(item, score) for item, score in location_matches if score]
    if location_matches:
        if len(location_matches) == 1:
            return LaboratoryResolution(location_matches[0][0], False, (), "location", 0.8)
        return LaboratoryResolution(
            None,
            True,
            tuple(item.name for item, _ in location_matches[:5]),
            "location_ambiguous",
            0.8,
        )

    fuzzy: list[tuple[Laboratory, float]] = []
    for item, name in normalized_names:
        score = SequenceMatcher(None, name, query).ratio()
        if score >= 0.72:
            fuzzy.append((item, score))
    fuzzy.sort(key=lambda pair: (-pair[1], pair[0].id))
    if not fuzzy:
        return LaboratoryResolution(None, False, (), "none", 0.0)
    best_item, best_score = fuzzy[0]
    second_score = fuzzy[1][1] if len(fuzzy) > 1 else 0.0
    if len(fuzzy) > 1 and best_score - second_score < 0.12:
        return LaboratoryResolution(
            None,
            True,
            tuple(item.name for item, _ in fuzzy[:5]),
            "fuzzy_ambiguous",
            best_score,
        )
    return LaboratoryResolution(best_item, False, (), "fuzzy", best_score)
