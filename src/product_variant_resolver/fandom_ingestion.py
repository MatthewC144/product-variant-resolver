from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FANDOM_API_URL = "https://hotwheels.fandom.com/api.php"
FANDOM_LICENSE_URL = "https://www.fandom.com/licensing"
FANDOM_USER_AGENT = (
    "ProductVariantResolverPilot/0.1 "
    "(https://github.com/MatthewC144/product-variant-resolver)"
)
MAX_API_RESPONSE_BYTES = 3_000_000
STAGING_SCHEMA_VERSION = "fandom-hot-wheels-staging-v1"


@dataclass(frozen=True, slots=True)
class FandomRevision:
    page_id: int
    page_title: str
    revision_id: int
    revision_timestamp: str
    wikitext: str


def _api_request(parameters: dict[str, str]) -> dict[str, Any]:
    url = f"{FANDOM_API_URL}?{urlencode(parameters)}"
    request = Request(url, headers={"User-Agent": FANDOM_USER_AGENT})
    with urlopen(request, timeout=30) as response:
        payload = response.read(MAX_API_RESPONSE_BYTES + 1)
    if len(payload) > MAX_API_RESPONSE_BYTES:
        raise ValueError("Fandom API response exceeds the 3 MB safety limit")
    result = json.loads(payload)
    if not isinstance(result, dict) or result.get("error"):
        raise ValueError("Fandom API returned an invalid or error response")
    return result


def fetch_rights_info() -> dict[str, str]:
    payload = _api_request(
        {
            "action": "query",
            "meta": "siteinfo",
            "siprop": "general|rightsinfo",
            "format": "json",
            "formatversion": "2",
        }
    )
    rights = payload.get("query", {}).get("rightsinfo", {})
    text = str(rights.get("text", "")).strip()
    url = str(rights.get("url", "")).strip()
    if text != "CC-BY-SA" or url != FANDOM_LICENSE_URL:
        raise ValueError("unexpected Fandom license; manual review is required")
    return {"name": text, "url": url}


def fetch_revision(page_title: str) -> FandomRevision:
    payload = _api_request(
        {
            "action": "query",
            "prop": "revisions",
            "titles": page_title,
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
            "format": "json",
            "formatversion": "2",
        }
    )
    pages = payload.get("query", {}).get("pages", [])
    if len(pages) != 1 or pages[0].get("missing"):
        raise ValueError("Fandom page was not found")
    page = pages[0]
    revisions = page.get("revisions", [])
    if len(revisions) != 1:
        raise ValueError("Fandom page did not return exactly one current revision")
    revision = revisions[0]
    content = revision.get("slots", {}).get("main", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Fandom revision has no wikitext content")
    return FandomRevision(
        page_id=int(page["pageid"]),
        page_title=str(page["title"]),
        revision_id=int(revision["revid"]),
        revision_timestamp=str(revision["timestamp"]),
        wikitext=content,
    )


def _clean_wikitext(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\{\{[^{}]*\}\}", " ", value)

    def link_text(match: re.Match[str]) -> str:
        parts = match.group(1).split("|")
        return parts[-1]

    value = re.sub(r"\[\[([^\[\]]+)\]\]", link_text, value)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("''", "")
    return " ".join(html.unescape(value).split())


def _table_cells(row: str) -> list[str]:
    cells: list[str] = []
    for raw_line in row.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("|"):
            value = line[1:]
            if value.startswith(("style=", "bgcolor=", "align=", "rowspan=", "colspan=")):
                _attributes, separator, value = value.partition("|")
                if not separator:
                    value = ""
            cells.append(value)
        elif cells:
            cells[-1] = f"{cells[-1]} {line}"
    return cells


def _variant_parts(model_label: str) -> tuple[str, str | None]:
    match = re.search(
        r"\s*\(((?:\d+(?:st|nd|rd|th)\s+)?Color(?:\s*-\s*[^)]+)?)\)\s*$",
        model_label,
        flags=re.IGNORECASE,
    )
    if not match:
        return model_label, None
    return model_label[:match.start()].strip(), match.group(1).strip()


def parse_mainline_records(
    revision: FandomRevision,
    *,
    release_year: int,
    limit: int,
    license_info: dict[str, str],
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 500:
        raise ValueError("pilot limit must be between 1 and 500")
    table_start = revision.wikitext.find('{|class="sortable wikitable"')
    if table_start < 0:
        raise ValueError("sortable mainline table was not found")
    table_end = revision.wikitext.find("\n|}", table_start)
    if table_end < 0:
        raise ValueError("mainline table is not closed")
    table = revision.wikitext[table_start:table_end]
    source_url = (
        "https://hotwheels.fandom.com/wiki/"
        f"{revision.page_title.replace(' ', '_')}?oldid={revision.revision_id}"
    )
    records: list[dict[str, Any]] = []
    source_row = 0
    for row in table.split("\n|-\n")[1:]:
        cells = _table_cells(row)
        if len(cells) < 5:
            continue
        toy_number = _clean_wikitext(cells[0])
        collector_number = _clean_wikitext(cells[1])
        model_label = _clean_wikitext(cells[2])
        series = _clean_wikitext(cells[3])
        series_position = _clean_wikitext(cells[4])
        if not toy_number or not model_label or not series:
            continue
        source_row += 1
        casting_name, variant_note = _variant_parts(model_label)
        markers = sorted(
            {
                marker.split("|", 1)[0].strip()
                for marker in re.findall(r"\{\{([^{}]+)\}\}", cells[2] + cells[3])
                if marker.strip()
            }
        )
        record_key = f"{release_year}:{toy_number}:{collector_number}:{source_row}"
        record_id = "fandom-row-" + hashlib.sha256(record_key.encode()).hexdigest()[:16]
        records.append(
            {
                "source_record_id": record_id,
                "source_row": source_row,
                "brand": "Hot Wheels",
                "release_year": release_year,
                "toy_number": toy_number,
                "collector_number": collector_number or None,
                "source_model_label": model_label,
                "casting_name": casting_name,
                "variant_note": variant_note,
                "series": series,
                "series_position": series_position or None,
                "color": None,
                "source_markers": markers,
                "canonical_uuid": None,
                "review_status": "needs_canonical_review",
                "usage": "staging_only_not_evaluation_or_canonical",
                "source": {
                    "page_title": revision.page_title,
                    "page_url": source_url,
                    "revision_id": revision.revision_id,
                    "revision_timestamp": revision.revision_timestamp,
                    "license": license_info["name"],
                    "license_url": license_info["url"],
                },
            }
        )
        if len(records) == limit:
            break
    if len(records) != limit:
        raise ValueError(f"expected {limit} valid records but parsed {len(records)}")
    return records


def stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
