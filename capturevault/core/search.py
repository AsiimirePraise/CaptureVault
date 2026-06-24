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
from capturevault.core.search_filters import SearchFilters
from capturevault.core.search_cache import SearchCache
from capturevault.database.manager import DatabaseManager


STAR_PATTERN = re.compile(r"(\d)\s*stars?", re.IGNORECASE)
COLOR_PATTERN = re.compile(
    r"\b(red|yellow|green|blue|purple)\b", re.IGNORECASE
)
EXT_QUERY = re.compile(
    r"^(?:\*?\.|ext:)([a-z0-9]+)$", re.IGNORECASE
)


def _parse_extension_query(text: str) -> str | None:
    """Detect extension searches: .doc, *.doc, ext:doc, .pdf"""
    raw = text.strip().lower()
    if not raw:
        return None

    match = EXT_QUERY.match(raw)
    if match:
        return f".{match.group(1)}"

    if raw.startswith(".") and len(raw) > 1 and raw[1:].replace("_", "").isalnum():
        return raw

    return None


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

    if _parse_extension_query(text):
        result["text"] = text
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
        "word": (FILE_TYPE_DOCUMENT,),
        "pdf": (FILE_TYPE_DOCUMENT,),
        "pdfs": (FILE_TYPE_DOCUMENT,),
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
        file_data.get("extension") or "",
        file_data.get("folder_name") or "",
        file_data.get("notes") or "",
        " ".join(tags),
        " ".join(collections),
    ]
    return " ".join(p for p in parts if p).lower()


def _letters_in_order(needle: str, haystack: str) -> bool:
    """True if all letters in needle appear in haystack in order."""
    i = 0
    for c in haystack.lower():
        if i < len(needle) and c == needle[i]:
            i += 1
    return i == len(needle)


def _min_match_score(text: str) -> float:
    """Lower bar for short / partial queries."""
    n = len(text.strip())
    if n <= 2:
        return 15.0
    if n <= 4:
        return 25.0
    return 35.0


def _score_match(query: str, searchable: str, file_data: dict) -> float:
    """Score a file against query. Virtual names weighted higher."""
    if not query:
        return 0.0

    q = query.lower()
    scores: list[float] = []

    virtual = (file_data.get("virtual_name") or "").lower()
    fname = (file_data.get("file_name") or "").lower()

    if virtual:
        scores.append(fuzz.partial_ratio(q, virtual) * 1.5)
        if _letters_in_order(q, virtual):
            scores.append(90.0)

    if fname:
        scores.append(fuzz.partial_ratio(q, fname) * 1.2)
        if _letters_in_order(q, fname):
            scores.append(85.0)
        if q in fname:
            scores.append(95.0)

    # Each word typed can match anywhere (e.g. "bride aisle" -> "Bride Walking Aisle")
    tokens = q.split()
    if len(tokens) > 1:
        token_hits = [fuzz.partial_ratio(t, searchable) for t in tokens if t]
        if token_hits:
            scores.append(min(token_hits) * 1.1)

    scores.append(fuzz.partial_ratio(q, searchable))
    scores.append(fuzz.token_set_ratio(q, searchable))

    if q in searchable:
        scores.append(100.0)

    return max(scores) if scores else 0.0


class SearchEngine:
    """Combines SQL fast-path, FTS5, and targeted fuzzy matching."""

    _cache = SearchCache()

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()

    def search(
        self,
        query: str,
        limit: int = 200,
        filters: SearchFilters | None = None,
    ) -> list[dict]:
        filters = filters or SearchFilters()

        cached = self._cache.get(query, filters)
        if cached is not None:
            return cached[:limit]

        results = self._search_uncached(query, limit, filters)
        self._cache.put(query, filters, results)
        return results[:limit]

    def _search_uncached(
        self,
        query: str,
        limit: int,
        filters: SearchFilters,
    ) -> list[dict]:
        parsed = _parse_query(query)

        if not parsed["text"] and any(
            parsed[k]
            for k in ("rating", "color", "favorites_only", "file_type")
        ):
            return self._filter_only(parsed, filters, limit)

        text = parsed["text"]
        has_ui_filters = (
            filters.type_filter != "all" or filters.folder_path is not None
        )

        if not text and not any(
            parsed[k]
            for k in ("rating", "color", "favorites_only", "file_type")
        ):
            if has_ui_filters:
                return self._browse_filtered(filters, limit)
            return self._light_enrich(
                self._db.get_recent_files(min(limit, 200))
            )

        extension = _parse_extension_query(text)
        if extension:
            files = self._db.get_files_by_extension(extension, limit=limit * 2)
            filtered = [
                f for f in files if self._passes_filters(f, parsed, filters)
            ]
            return self._light_enrich(filtered[:limit])

        # Fast SQL path — filename search (fastest for most queries)
        if text and len(text) >= 2:
            scoped = self._db.search_scoped(
                text,
                extensions=filters.extensions(),
                folder_prefix=filters.folder_path,
                limit=limit,
            )
            if scoped:
                filtered = [
                    f for f in scoped if self._passes_filters(f, parsed, filters)
                ]
                if filtered:
                    return self._light_enrich(filtered[:limit])

        like_limit = 400 if len(text) <= 4 else 300
        fts_ids = self._db.search_fts(text, limit=limit * 2)
        like_ids = self._db.search_like(text, limit=like_limit)
        candidate_ids = list(dict.fromkeys(fts_ids + like_ids))
        like_set = set(like_ids)
        fts_set = set(fts_ids)

        candidates = (
            self._db.get_files_by_ids(candidate_ids) if candidate_ids else []
        )

        # Small fuzzy fallback only when SQL found almost nothing
        if text and len(candidates) < min(limit, 20):
            pool = self._get_search_pool(filters, limit=600)
            pool_ids = {c["id"] for c in candidates}
            min_score = _min_match_score(text)
            for file_data in pool:
                if file_data["id"] in pool_ids:
                    continue
                if not self._passes_filters(file_data, parsed, filters):
                    continue
                searchable = _build_searchable_text(file_data, [], [])
                if _score_match(text, searchable, file_data) >= min_score:
                    candidates.append(file_data)
                    pool_ids.add(file_data["id"])
                if len(candidates) >= limit:
                    break

        id_order = {fid: i for i, fid in enumerate(candidate_ids)}

        results: list[tuple[float, dict]] = []
        for file_data in candidates:
            if not self._passes_filters(file_data, parsed, filters):
                continue

            fid = file_data["id"]
            searchable = _build_searchable_text(file_data, [], [])

            if text:
                score = _score_match(text, searchable, file_data)
                min_score = _min_match_score(text)
                if (
                    score < min_score
                    and fid not in fts_set
                    and fid not in like_set
                ):
                    continue
                if fid in fts_set:
                    score += 10
                if fid in like_set:
                    score += 5
            else:
                score = 100.0

            item = dict(file_data)
            item["tags"] = []
            item["collections"] = []
            item["_score"] = score
            results.append((score, item))

        results.sort(
            key=lambda x: (-x[0], id_order.get(x[1]["id"], 999999))
        )
        return [r[1] for r in results[:limit]]

    def _browse_filtered(
        self, filters: SearchFilters, limit: int
    ) -> list[dict]:
        """List files matching UI type/folder filters with no search text."""
        exts = filters.extensions()
        if exts:
            files = self._db.get_files_by_extensions(
                exts,
                folder_prefix=filters.folder_path,
                limit=limit * 2,
            )
        else:
            types = filters.file_types()
            if types:
                files = self._db.get_files_by_types(
                    types, folder_prefix=filters.folder_path, limit=limit * 2
                )
            elif filters.folder_path:
                files = self._db.get_files_in_folder(
                    filters.folder_path, limit=limit * 2
                )
            else:
                files = self._db.get_recent_files(limit)

        filtered = [f for f in files if filters.matches_file(f)]
        return self._light_enrich(filtered[:limit])

    def _get_search_pool(
        self, filters: SearchFilters, limit: int = 600
    ) -> list[dict]:
        """Files to scan for fuzzy matching within current filters."""
        exts = filters.extensions()
        if exts:
            files = self._db.get_files_by_extensions(
                exts,
                folder_prefix=filters.folder_path,
                limit=limit,
            )
        else:
            types = filters.file_types()
            if types:
                files = self._db.get_files_by_types(
                    types, folder_prefix=filters.folder_path, limit=limit
                )
            elif filters.folder_path:
                files = self._db.get_files_in_folder(
                    filters.folder_path, limit=limit
                )
            else:
                files = self._db.get_all_files(limit=limit)
        return [f for f in files if filters.matches_file(f)]

    @staticmethod
    def _light_enrich(files: list[dict]) -> list[dict]:
        """Skip tag/collection DB lookups — not shown in the results grid."""
        return [
            {**dict(f), "tags": [], "collections": []}
            for f in files
        ]

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

    def _passes_filters(
        self,
        file_data: dict,
        parsed: dict,
        filters: SearchFilters,
    ) -> bool:
        if not filters.matches_file(file_data):
            return False
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

    def _filter_only(
        self,
        parsed: dict,
        filters: SearchFilters,
        limit: int,
    ) -> list[dict]:
        if parsed["rating"] is not None:
            files = self._db.get_files_by_rating(parsed["rating"])
        elif parsed["color"]:
            files = self._db.get_files_by_color(parsed["color"])
        elif parsed["favorites_only"]:
            files = self._db.get_favorites()
        else:
            files = self._browse_filtered(filters, limit * 2)
            if parsed["file_type"]:
                files = [
                    f
                    for f in files
                    if f.get("file_type") in parsed["file_type"]
                ]
            return self._light_enrich(files[:limit])

        if parsed["file_type"]:
            files = [
                f for f in files if f.get("file_type") in parsed["file_type"]
            ]

        files = [f for f in files if filters.matches_file(f)]
        return self._light_enrich(files[:limit])
