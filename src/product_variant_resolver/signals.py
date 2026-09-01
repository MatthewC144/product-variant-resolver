from __future__ import annotations

import re

from .identity import normalize_text
from .schemas import ExtractedSignals

YEAR_RE = re.compile(r"(?<!\d)(19[6-9]\d|20[0-4]\d)(?!\d)")
SERIES_POSITION_RE = re.compile(r"(?<!\d)(\d{1,3})\s*/\s*(\d{1,3})(?!\d)")
COLLECTOR_RE = re.compile(r"(?:#|no\.?\s*)([a-z]?\d{1,5}[a-z]?)(?!\w)", re.IGNORECASE)
QUANTITY_RE = re.compile(r"(?:lot\s+of|qty|quantity|x)\s*[:x]?\s*(\d{1,3})(?!\d)", re.IGNORECASE)
PACK_RE = re.compile(r"(?<!\d)(\d{1,2})[ -]?(?:pack|pk)(?!\w)", re.IGNORECASE)
NOISE_TOKENS = frozenset({"nib", "nip", "new", "sealed", "rare", "vhtf", "htf", "hotwheels"})


def _catalog_hints(normalized_title: str, vocabulary: set[str] | frozenset[str] | None) -> list[str]:
    """Match catalog-provided single- or multi-token phrases on token boundaries."""

    padded_title = f" {normalized_title} "
    normalized_values = {normalize_text(value) for value in (vocabulary or set()) if value}
    return sorted(value for value in normalized_values if f" {value} " in padded_title)


def extract_signals(
    title: str,
    color_vocabulary: set[str] | frozenset[str] | None = None,
    series_vocabulary: set[str] | frozenset[str] | None = None,
) -> ExtractedSignals:
    normalized = normalize_text(title)
    tokens = normalized.split()
    year_match = YEAR_RE.search(title)
    position_match = SERIES_POSITION_RE.search(title)
    collector_match = COLLECTOR_RE.search(title)
    quantity_match = QUANTITY_RE.search(title) or PACK_RE.search(title)
    quantity = int(quantity_match.group(1)) if quantity_match else None
    warnings: list[str] = []
    years = YEAR_RE.findall(title)
    if len(set(years)) > 1:
        warnings.append("multiple_years")
    if position_match and int(position_match.group(1)) > int(position_match.group(2)):
        warnings.append("invalid_series_position")
    cleaned_tokens = [token for token in tokens if token not in NOISE_TOKENS]
    colors = _catalog_hints(normalized, color_vocabulary)
    series = _catalog_hints(normalized, series_vocabulary)
    return ExtractedSignals(
        normalized_title=normalized,
        tokens=cleaned_tokens,
        year=int(year_match.group(1)) if year_match else None,
        collector_number=collector_match.group(1).casefold() if collector_match else None,
        series_position=(f"{int(position_match.group(1))}/{int(position_match.group(2))}"
                         if position_match else None),
        quantity=quantity,
        multipack_hint=bool(quantity and quantity > 1),
        color_hints=colors,
        series_hints=series,
        parse_warnings=warnings,
    )
