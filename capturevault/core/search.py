"""Fast search engine with fuzzy matching."""

import re
from typing import Any

from rapidfuzz import fuzz

from capturevault.constants import (
    COLOR_LABELS,
    FILE_TYPE_DOCUMENT,
    FILE_TYPE_IMAGE,
    FILE_TYPE_RAW,
    FILE_TYPE_VIDEO,
    RATING_QUERY_PREFIX,
)
from capturevault.database.manager import DatabaseManager


STAR_PATTERN = re.compile(r"(\d)\s*stars?", re.IGNORECASE)
COLOR_PATTERN = re.compile(
    r"\b(red|yellow|green|blue|purple)\b", re.IGNORECASE
)


def _parse_query(query: str) -> dict[str, Any]:
    """Extract special search modifiers from query string."""
    text = query.strip()
    result: dict[str, Any] = {
        "text": text,
        "rating": None,
        "color": None,
        "favorites_only": False,
        "file_type": None,
    }

    if not text:
        return result

    rating_match = re.search(
        rf"{RATING_QUERY_PREFIX}(\d)", text, re.IGNORECASE
    )
    if rating_match:
        result["rating"] = int(rating_match.group(1))
        text = re.sub(
            rf"{RATING_QUERY_PREFIX}\d+", "", text, flags=re.IGNORECASE
        ).strip()

    star_match = STAR_PATTERN.search(text)
    if star_match:
        result["rating"] = int(star_match.group(1))
        text = STAR_PATTERN.sub("", text).strip()

    if re.search(r"\bfavorites?\b", text, re.IGNORECASE):
        result["favorites_only"] = True
        text = re.sub(r"\bfavorites?\b", "", text, flags=re.IGNORECASE).strip()

    lower = text.lower()
    type_keywords = {
        "photos": (FILE_TYPE_IMAGE, FILE_TYPE_RAW),
        "photo": (FILE_TYPE_IMAGE, FILE_TYPE_RAW),
        "images": (FILE_TYPE_IMAGE,),
        "image": (FILE_TYPE_IMAGE,),
        "videos": (FILE_TYPE_VIDEO,),
        "video": (FILE_TYPE_VIDEO,),
        "documents": (FILE_TYPE_DOCUMENT,),
        "document": (FILE_TYPE_DOCUMENT,),
    }
    for keyword, types in type_keywords.items():
        if re.search(rf"\b{keyword}\b", lower):
            result["file_type"] = types
            text = re.sub(
                rf"\b{keyword}\b", "", text, flags=re.IGNORECASE
            ).strip()
            break

    color_match = COLOR_PATTERN.search(text)
    if color_match:
        color = color_match.group(1).lower()
        if color in COLOR_LABELS:
            result["color"] = color
        text = COLOR_PATTERN.sub("", text).strip()

    result["text"] = text.strip()
    return result


def _build_searchable_text(
    file_data: dict, tags: list[str], collections: list[str]
) -> str:
    parts = [
        file_data.get("virtual_name") or "",
        file_data.get("file_name") or "",
        file_data.get("folder_name") or "",
        file_data.get("notes") or "",
        " ".join(tags),
        " ".join(collections),
    ]
    return " ".join(p for p in parts if p).lower()


def _score_match(query: str, searchable: str, file_data: dict) -> float:
    """Score a file against query. Virtual names weighted higher."""
    if not query:
        return 0.0

    q = query.lower()
    scores: list[float] = []

    virtual = (file_data.get("virtual_name") or "").lower()
    if virtual:
        scores.append(fuzz.partial_ratio(q, virtual) * 1.5)

    scores.append(fuzz.partial_ratio(q, searchable))
    scores.append(fuzz.token_set_ratio(q, searchable))

    if q in searchable:
        scores.append(100.0)

    return max(scores) if scores else 0.0


class SearchEngine:
    """Combines FTS5 / SQL pre-filtering with fuzzy re-ranking."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def search(self, query: str, limit: int = 200) -> list[dict]:
        parsed = _parse_query(query)

        if not parsed["text"] and any(
            parsed[k]
            for k in ("rating", "color", "favorites_only", "file_type")
        ):
            return self._filter_only(parsed, limit)

        text = parsed["text"]
        if not text and not any(
            parsed[k]
            for k in ("rating", "color", "favorites_only", "file_type")
        ):
            return self._enrich_files(self._db.get_recent_files(limit))

        fts_ids = self._db.search_fts(text, limit=limit * 3)
        like_ids = self._db.search_like(text, limit=limit * 3)
        candidate_ids = list(dict.fromkeys(fts_ids + like_ids))
        like_set = set(like_ids)

        if candidate_ids:
            candidates = self._db.get_files_by_ids(candidate_ids)
        else:
            candidates = []

        id_order = {fid: i for i, fid in enumerate(candidate_ids)}
        fts_set = set(fts_ids)

        file_ids = [f["id"] for f in candidates]
        tags_map = self._db.get_tags_map_for_files(file_ids)
        collections_map = self._db.get_collections_map_for_files(file_ids)

        results: list[tuple[float, dict]] = []
        for file_data in candidates:
            if not self._passes_filters(file_data, parsed):
                continue

            fid = file_data["id"]
            tags = tags_map.get(fid, [])
            collections = collections_map.get(fid, [])
            searchable = _build_searchable_text(file_data, tags, collections)

            if text:
                score = _score_match(text, searchable, file_data)
                if score < 40 and fid not in fts_set and fid not in like_set:
                    continue
                # Prefer virtual-name matches and FTS hits
                if fid in fts_set:
                    score += 10
                if fid in like_ids:
                    score += 5
            else:
                score = 100.0

            enriched = dict(file_data)
            enriched["tags"] = tags
            enriched["collections"] = collections
            enriched["_score"] = score
            results.append((score, enriched))

        results.sort(
            key=lambda x: (-x[0], id_order.get(x[1]["id"], 999999))
        )
        return [r[1] for r in results[:limit]]

    def _enrich_files(self, files: list[dict]) -> list[dict]:
        if not files:
            return []
        file_ids = [f["id"] for f in files]
        tags_map = self._db.get_tags_map_for_files(file_ids)
        collections_map = self._db.get_collections_map_for_files(file_ids)
        enriched = []
        for file_data in files:
            item = dict(file_data)
            item["tags"] = tags_map.get(file_data["id"], [])
            item["collections"] = collections_map.get(file_data["id"], [])
            enriched.append(item)
        return enriched

    def _passes_filters(self, file_data: dict, parsed: dict) -> bool:
        if parsed["rating"] is not None:
            if file_data.get("rating", 0) != parsed["rating"]:
                return False
        if parsed["color"]:
            if (file_data.get("color_label") or "").lower() != parsed["color"]:
                return False
        if parsed["favorites_only"]:
            if not file_data.get("is_favorite"):
                return False
        if parsed["file_type"]:
            if file_data.get("file_type") not in parsed["file_type"]:
                return False
        return True

    def _filter_only(self, parsed: dict, limit: int) -> list[dict]:
        if parsed["rating"] is not None:
            files = self._db.get_files_by_rating(parsed["rating"])
        elif parsed["color"]:
            files = self._db.get_files_by_color(parsed["color"])
        elif parsed["favorites_only"]:
            files = self._db.get_favorites()
        else:
            files = self._db.get_all_files(limit)

        if parsed["file_type"]:
            files = [
                f for f in files if f.get("file_type") in parsed["file_type"]
            ]

        return self._enrich_files(files[:limit])
