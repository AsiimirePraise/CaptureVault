"""In-memory cache for recent search queries."""

from __future__ import annotations

from capturevault.core.search_filters import SearchFilters


class SearchCache:
    """Small LRU-style cache for instant repeat searches."""

    def __init__(self, max_entries: int = 48) -> None:
        self._max = max_entries
        self._data: dict[tuple, list[dict]] = {}
        self._order: list[tuple] = []

    @staticmethod
    def _key(query: str, filters: SearchFilters) -> tuple:
        return (
            query.strip().lower(),
            filters.type_filter,
            (filters.folder_path or "").lower(),
        )

    def get(self, query: str, filters: SearchFilters) -> list[dict] | None:
        key = self._key(query, filters)
        hit = self._data.get(key)
        if hit is None:
            return None
        return [dict(r) for r in hit]

    def put(self, query: str, filters: SearchFilters, results: list[dict]) -> None:
        key = self._key(query, filters)
        if key in self._data:
            self._order.remove(key)
        elif len(self._order) >= self._max:
            oldest = self._order.pop(0)
            self._data.pop(oldest, None)
        self._order.append(key)
        self._data[key] = [dict(r) for r in results]

    def clear(self) -> None:
        self._data.clear()
        self._order.clear()
