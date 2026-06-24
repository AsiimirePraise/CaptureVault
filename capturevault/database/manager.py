"""SQLite database manager for CaptureVault."""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from capturevault.constants import ALL_EXTENSIONS, COLOR_LABELS


def _classify_extension(ext: str) -> str:
    """Map file extension to file type category."""
    from capturevault.constants import (
        AUDIO_EXTENSIONS,
        DOCUMENT_EXTENSIONS,
        FILE_TYPE_AUDIO,
        FILE_TYPE_DOCUMENT,
        FILE_TYPE_IMAGE,
        FILE_TYPE_OTHER,
        FILE_TYPE_RAW,
        FILE_TYPE_VIDEO,
        IMAGE_EXTENSIONS,
        RAW_EXTENSIONS,
        VIDEO_EXTENSIONS,
    )

    ext = ext.lower()
    if ext in IMAGE_EXTENSIONS:
        return FILE_TYPE_IMAGE
    if ext in RAW_EXTENSIONS:
        return FILE_TYPE_RAW
    if ext in VIDEO_EXTENSIONS:
        return FILE_TYPE_VIDEO
    if ext in AUDIO_EXTENSIONS:
        return FILE_TYPE_AUDIO
    if ext in DOCUMENT_EXTENSIONS:
        return FILE_TYPE_DOCUMENT
    return FILE_TYPE_OTHER


def folder_like_pattern(folder_prefix: str) -> str:
    """Build SQL LIKE pattern for a folder (handles D: vs D:\\ paths)."""
    p = folder_prefix.strip().rstrip("\\/")
    p = p.replace("/", "\\")
    if len(p) == 2 and p[1] == ":":
        return p[0].upper() + p[1] + "%"
    return p + "%"


class DatabaseManager:
    """Thread-safe SQLite access layer."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self) -> None:
        schema_path = Path(__file__).parent / "schema.sql"
        schema = schema_path.read_text(encoding="utf-8")
        with self._lock:
            conn = self._connect()
            conn.executescript(schema)
            conn.commit()

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            conn = self._connect()
            cur = conn.execute(sql, params)
            conn.commit()
            return cur

    def _fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            conn = self._connect()
            return conn.execute(sql, params).fetchall()

    def _fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            conn = self._connect()
            return conn.execute(sql, params).fetchone()

    # --- Monitored folders ---

    def get_monitored_folders(self) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT id, path, added_at FROM monitored_folders ORDER BY path"
        )
        return [dict(r) for r in rows]

    def add_monitored_folder(self, path: str) -> bool:
        normalized = str(Path(path).resolve())
        try:
            self._execute(
                "INSERT INTO monitored_folders (path) VALUES (?)",
                (normalized,),
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_monitored_folder(self, folder_id: int) -> None:
        self._execute("DELETE FROM monitored_folders WHERE id = ?", (folder_id,))

    def has_monitored_folders(self) -> bool:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM monitored_folders")
        return bool(row and row["cnt"] > 0)

    # --- File indexing ---

    @staticmethod
    def is_supported_file(path: Path) -> bool:
        return path.suffix.lower() in ALL_EXTENSIONS

    def upsert_file(self, file_path: Path) -> int | None:
        """Insert or update file metadata. Returns file id."""
        if not file_path.is_file():
            return None
        ext = file_path.suffix.lower()
        if ext not in ALL_EXTENSIONS:
            return None

        stat = file_path.stat()
        created = datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
        folder_name = file_path.parent.name
        file_type = _classify_extension(ext)

        with self._lock:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO files (
                    path, file_name, folder_name, extension, file_type,
                    file_size, date_created, date_modified, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(path) DO UPDATE SET
                    file_name = excluded.file_name,
                    folder_name = excluded.folder_name,
                    extension = excluded.extension,
                    file_type = excluded.file_type,
                    file_size = excluded.file_size,
                    date_created = excluded.date_created,
                    date_modified = excluded.date_modified,
                    indexed_at = datetime('now')
                """,
                (
                    str(file_path.resolve()),
                    file_path.name,
                    folder_name,
                    ext,
                    file_type,
                    stat.st_size,
                    created,
                    modified,
                ),
            )
            row = conn.execute(
                "SELECT id FROM files WHERE path = ?",
                (str(file_path.resolve()),),
            ).fetchone()
            conn.commit()
            if row:
                self._rebuild_file_fts(row["id"])
                return row["id"]
        return None

    def get_file_by_path(self, path: str) -> dict[str, Any] | None:
        row = self._fetchone("SELECT * FROM files WHERE path = ?", (path,))
        return dict(row) if row else None

    def get_file_by_id(self, file_id: int) -> dict[str, Any] | None:
        row = self._fetchone("SELECT * FROM files WHERE id = ?", (file_id,))
        return dict(row) if row else None

    def get_all_indexed_paths(self) -> dict[str, dict[str, Any]]:
        rows = self._fetchall("SELECT id, path, date_modified FROM files")
        return {r["path"]: dict(r) for r in rows}

    def remove_file_by_path(self, path: str) -> None:
        row = self._fetchone("SELECT id FROM files WHERE path = ?", (path,))
        if row:
            self._execute("DELETE FROM files WHERE id = ?", (row["id"],))
            self._execute("DELETE FROM files_fts WHERE rowid = ?", (row["id"],))

    def remove_files_under_folder(self, folder_path: str) -> None:
        prefix = str(Path(folder_path).resolve())
        rows = self._fetchall(
            "SELECT id FROM files WHERE path LIKE ?",
            (prefix + "%",),
        )
        for row in rows:
            self._execute("DELETE FROM files WHERE id = ?", (row["id"],))
            self._execute("DELETE FROM files_fts WHERE rowid = ?", (row["id"],))

    # --- FTS ---

    def _get_tags_text(self, file_id: int) -> str:
        rows = self._fetchall(
            """
            SELECT t.name FROM tags t
            JOIN file_tags ft ON ft.tag_id = t.id
            WHERE ft.file_id = ?
            """,
            (file_id,),
        )
        return " ".join(r["name"] for r in rows)

    def _get_collections_text(self, file_id: int) -> str:
        rows = self._fetchall(
            """
            SELECT c.name FROM collections c
            JOIN file_collections fc ON fc.collection_id = c.id
            WHERE fc.file_id = ?
            """,
            (file_id,),
        )
        return " ".join(r["name"] for r in rows)

    def _rebuild_file_fts(self, file_id: int) -> None:
        row = self._fetchone("SELECT * FROM files WHERE id = ?", (file_id,))
        if not row:
            return
        tags_text = self._get_tags_text(file_id)
        collections_text = self._get_collections_text(file_id)
        with self._lock:
            conn = self._connect()
            conn.execute("DELETE FROM files_fts WHERE rowid = ?", (file_id,))
            conn.execute(
                """
                INSERT INTO files_fts (
                    rowid, file_name, virtual_name, notes,
                    folder_name, tags_text, collections_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    row["file_name"] or "",
                    row["virtual_name"] or "",
                    row["notes"] or "",
                    row["folder_name"] or "",
                    tags_text,
                    collections_text,
                ),
            )
            conn.commit()

    def rebuild_all_fts(self) -> None:
        rows = self._fetchall("SELECT id FROM files")
        for row in rows:
            self._rebuild_file_fts(row["id"])

    # --- Metadata updates ---

    def update_file_metadata(
        self,
        file_id: int,
        virtual_name: str | None = None,
        notes: str | None = None,
        rating: int | None = None,
        color_label: str | None = None,
        is_favorite: bool | None = None,
    ) -> None:
        updates: list[str] = []
        params: list[Any] = []

        if virtual_name is not None:
            updates.append("virtual_name = ?")
            params.append(virtual_name.strip() or None)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes.strip() or None)
        if rating is not None:
            updates.append("rating = ?")
            params.append(max(0, min(5, rating)))
        if color_label is not None:
            label = color_label.lower() if color_label else None
            if label and label not in COLOR_LABELS:
                label = None
            updates.append("color_label = ?")
            params.append(label)
        if is_favorite is not None:
            updates.append("is_favorite = ?")
            params.append(1 if is_favorite else 0)

        if not updates:
            return

        params.append(file_id)
        self._execute(
            f"UPDATE files SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        self._rebuild_file_fts(file_id)

    # --- Tags ---

    def get_file_tags(self, file_id: int) -> list[str]:
        rows = self._fetchall(
            """
            SELECT t.name FROM tags t
            JOIN file_tags ft ON ft.tag_id = t.id
            WHERE ft.file_id = ?
            ORDER BY t.name
            """,
            (file_id,),
        )
        return [r["name"] for r in rows]

    def set_file_tags(self, file_id: int, tag_names: list[str]) -> None:
        normalized = []
        for name in tag_names:
            name = name.strip().lstrip("#")
            if name:
                normalized.append(name)

        with self._lock:
            conn = self._connect()
            conn.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id,))
            for name in normalized:
                conn.execute(
                    "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                    (name,),
                )
                tag_row = conn.execute(
                    "SELECT id FROM tags WHERE name = ? COLLATE NOCASE",
                    (name,),
                ).fetchone()
                if tag_row:
                    conn.execute(
                        "INSERT OR IGNORE INTO file_tags (file_id, tag_id) "
                        "VALUES (?, ?)",
                        (file_id, tag_row["id"]),
                    )
            conn.commit()
        self._rebuild_file_fts(file_id)

    # --- Collections ---

    def get_collections(self) -> list[dict[str, Any]]:
        rows = self._fetchall(
            """
            SELECT c.*, COUNT(fc.file_id) AS file_count
            FROM collections c
            LEFT JOIN file_collections fc ON fc.collection_id = c.id
            GROUP BY c.id
            ORDER BY c.name
            """
        )
        return [dict(r) for r in rows]

    def create_collection(self, name: str, description: str = "") -> int | None:
        try:
            cur = self._execute(
                "INSERT INTO collections (name, description) VALUES (?, ?)",
                (name.strip(), description.strip()),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

    def delete_collection(self, collection_id: int) -> None:
        self._execute("DELETE FROM collections WHERE id = ?", (collection_id,))

    def get_file_collections(self, file_id: int) -> list[str]:
        rows = self._fetchall(
            """
            SELECT c.name FROM collections c
            JOIN file_collections fc ON fc.collection_id = c.id
            WHERE fc.file_id = ?
            ORDER BY c.name
            """,
            (file_id,),
        )
        return [r["name"] for r in rows]

    def set_file_collections(
        self, file_id: int, collection_names: list[str]
    ) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                "DELETE FROM file_collections WHERE file_id = ?", (file_id,)
            )
            for name in collection_names:
                name = name.strip()
                if not name:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO collections (name) VALUES (?)",
                    (name,),
                )
                col = conn.execute(
                    "SELECT id FROM collections WHERE name = ?",
                    (name,),
                ).fetchone()
                if col:
                    conn.execute(
                        "INSERT OR IGNORE INTO file_collections "
                        "(file_id, collection_id) VALUES (?, ?)",
                        (file_id, col["id"]),
                    )
            conn.commit()
        self._rebuild_file_fts(file_id)

    def add_file_to_collection(self, file_id: int, collection_id: int) -> None:
        self._execute(
            "INSERT OR IGNORE INTO file_collections (file_id, collection_id) "
            "VALUES (?, ?)",
            (file_id, collection_id),
        )
        self._rebuild_file_fts(file_id)

    def remove_file_from_collection(
        self, file_id: int, collection_id: int
    ) -> None:
        self._execute(
            "DELETE FROM file_collections WHERE file_id = ? AND collection_id = ?",
            (file_id, collection_id),
        )
        self._rebuild_file_fts(file_id)

    # --- Queries ---

    def get_files_by_collection(self, collection_id: int) -> list[dict]:
        rows = self._fetchall(
            """
            SELECT f.* FROM files f
            JOIN file_collections fc ON fc.file_id = f.id
            WHERE fc.collection_id = ?
            ORDER BY f.date_modified DESC
            """,
            (collection_id,),
        )
        return [dict(r) for r in rows]

    def get_favorites(self) -> list[dict]:
        rows = self._fetchall(
            "SELECT * FROM files WHERE is_favorite = 1 ORDER BY date_modified DESC"
        )
        return [dict(r) for r in rows]

    def get_recent_files(self, limit: int = 20) -> list[dict]:
        rows = self._fetchall(
            "SELECT * FROM files ORDER BY indexed_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    def get_dashboard_stats(self) -> dict[str, int]:
        row = self._fetchone(
            """
            SELECT
                COUNT(*) AS total_files,
                SUM(CASE WHEN file_type IN ('image', 'raw') THEN 1 ELSE 0 END) AS total_photos,
                SUM(CASE WHEN file_type = 'video' THEN 1 ELSE 0 END) AS total_videos,
                SUM(CASE WHEN file_type = 'document' THEN 1 ELSE 0 END) AS total_documents,
                SUM(CASE WHEN is_favorite = 1 THEN 1 ELSE 0 END) AS total_favorites
            FROM files
            """
        )
        if not row:
            return {
                "total_files": 0,
                "total_photos": 0,
                "total_videos": 0,
                "total_documents": 0,
                "total_favorites": 0,
            }
        return {k: int(row[k] or 0) for k in row.keys()}

    def search_fts(self, query: str, limit: int = 500) -> list[int]:
        """FTS5 prefix search returning file IDs."""
        if not query.strip():
            return []
        # Escape FTS special chars and build prefix tokens
        tokens = []
        for token in query.strip().split():
            # Keep extension tokens like .doc intact
            if token.startswith(".") and len(token) > 1:
                tokens.append(f'"{token.lower()}"*')
                continue
            cleaned = "".join(
                c for c in token if c.isalnum() or c in ("_", "-")
            )
            if cleaned:
                tokens.append(f'"{cleaned}"*')
        if not tokens:
            return []
        fts_query = " ".join(tokens)
        try:
            rows = self._fetchall(
                """
                SELECT rowid FROM files_fts
                WHERE files_fts MATCH ?
                LIMIT ?
                """,
                (fts_query, limit),
            )
            return [r["rowid"] for r in rows]
        except sqlite3.OperationalError:
            return []

    def get_files_by_ids(self, file_ids: list[int]) -> list[dict]:
        if not file_ids:
            return []
        placeholders = ",".join("?" * len(file_ids))
        rows = self._fetchall(
            f"SELECT * FROM files WHERE id IN ({placeholders})",
            tuple(file_ids),
        )
        return [dict(r) for r in rows]

    def get_all_files(self, limit: int = 500) -> list[dict]:
        rows = self._fetchall(
            "SELECT * FROM files ORDER BY date_modified DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    def search_like(self, query: str, limit: int = 600) -> list[int]:
        """Fast LIKE search across file fields, tags, and collections."""
        if not query.strip():
            return []
        pattern = f"%{query.strip()}%"
        rows = self._fetchall(
            """
            SELECT DISTINCT f.id FROM files f
            LEFT JOIN file_tags ft ON ft.file_id = f.id
            LEFT JOIN tags t ON t.id = ft.tag_id
            LEFT JOIN file_collections fc ON fc.file_id = f.id
            LEFT JOIN collections c ON c.id = fc.collection_id
            WHERE f.file_name LIKE ? COLLATE NOCASE
               OR f.virtual_name LIKE ? COLLATE NOCASE
               OR f.folder_name LIKE ? COLLATE NOCASE
               OR f.notes LIKE ? COLLATE NOCASE
               OR f.extension LIKE ? COLLATE NOCASE
               OR t.name LIKE ? COLLATE NOCASE
               OR c.name LIKE ? COLLATE NOCASE
            LIMIT ?
            """,
            (
                pattern, pattern, pattern, pattern, pattern,
                pattern, pattern, limit,
            ),
        )
        return [r["id"] for r in rows]

    def get_files_by_extension(
        self, extension: str, limit: int = 500
    ) -> list[dict]:
        """Find all files with a given extension, e.g. .doc or .pdf."""
        ext = extension.lower().strip()
        if not ext.startswith("."):
            ext = f".{ext}"
        rows = self._fetchall(
            """
            SELECT * FROM files
            WHERE extension = ? COLLATE NOCASE
            ORDER BY date_modified DESC
            LIMIT ?
            """,
            (ext, limit),
        )
        return [dict(r) for r in rows]

    def get_files_by_types(
        self,
        file_types: tuple[str, ...] | list[str],
        folder_prefix: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """Find files matching one or more file_type values."""
        if not file_types:
            return []
        placeholders = ",".join("?" * len(file_types))
        params: list = list(file_types)
        sql = f"""
            SELECT * FROM files
            WHERE file_type IN ({placeholders})
        """
        if folder_prefix:
            sql += " AND path LIKE ? COLLATE NOCASE"
            params.append(folder_like_pattern(folder_prefix))
        sql += " ORDER BY date_modified DESC LIMIT ?"
        params.append(limit)
        rows = self._fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_files_by_extensions(
        self,
        extensions: frozenset[str] | list[str],
        folder_prefix: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """Find files matching one or more extensions (e.g. all Word docs)."""
        if not extensions:
            return []
        ext_list = [
            e if e.startswith(".") else f".{e}" for e in extensions
        ]
        placeholders = ",".join("?" * len(ext_list))
        params: list = list(ext_list)
        sql = f"""
            SELECT * FROM files
            WHERE extension IN ({placeholders})
        """
        if folder_prefix:
            sql += " AND path LIKE ? COLLATE NOCASE"
            params.append(folder_like_pattern(folder_prefix))
        sql += " ORDER BY date_modified DESC LIMIT ?"
        params.append(limit)
        rows = self._fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    def search_scoped(
        self,
        query: str,
        extensions: frozenset[str] | list[str] | None = None,
        folder_prefix: str | None = None,
        limit: int = 300,
    ) -> list[dict]:
        """Search file names within optional extension and folder scope."""
        if not query.strip():
            return []
        pattern = f"%{query.strip()}%"
        params: list = [pattern, pattern, pattern, pattern]
        sql = """
            SELECT * FROM files
            WHERE (
                file_name LIKE ? COLLATE NOCASE
                OR virtual_name LIKE ? COLLATE NOCASE
                OR notes LIKE ? COLLATE NOCASE
                OR folder_name LIKE ? COLLATE NOCASE
            )
        """
        if extensions:
            ext_list = [
                e if e.startswith(".") else f".{e}" for e in extensions
            ]
            ph = ",".join("?" * len(ext_list))
            sql += f" AND extension IN ({ph})"
            params.extend(ext_list)
        if folder_prefix:
            sql += " AND path LIKE ? COLLATE NOCASE"
            params.append(folder_like_pattern(folder_prefix))
        sql += " ORDER BY date_modified DESC LIMIT ?"
        params.append(limit)
        rows = self._fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_files_in_folder(
        self, folder_prefix: str, limit: int = 500
    ) -> list[dict]:
        """Find all indexed files under a folder path."""
        rows = self._fetchall(
            """
            SELECT * FROM files
            WHERE path LIKE ? COLLATE NOCASE
            ORDER BY date_modified DESC
            LIMIT ?
            """,
            (folder_like_pattern(folder_prefix), limit),
        )
        return [dict(r) for r in rows]

    def get_tags_map_for_files(self, file_ids: list[int]) -> dict[int, list[str]]:
        if not file_ids:
            return {}
        placeholders = ",".join("?" * len(file_ids))
        rows = self._fetchall(
            f"""
            SELECT ft.file_id, t.name FROM tags t
            JOIN file_tags ft ON ft.tag_id = t.id
            WHERE ft.file_id IN ({placeholders})
            ORDER BY t.name
            """,
            tuple(file_ids),
        )
        result: dict[int, list[str]] = {fid: [] for fid in file_ids}
        for row in rows:
            result[row["file_id"]].append(row["name"])
        return result

    def get_collections_map_for_files(
        self, file_ids: list[int]
    ) -> dict[int, list[str]]:
        if not file_ids:
            return {}
        placeholders = ",".join("?" * len(file_ids))
        rows = self._fetchall(
            f"""
            SELECT fc.file_id, c.name FROM collections c
            JOIN file_collections fc ON fc.collection_id = c.id
            WHERE fc.file_id IN ({placeholders})
            ORDER BY c.name
            """,
            tuple(file_ids),
        )
        result: dict[int, list[str]] = {fid: [] for fid in file_ids}
        for row in rows:
            result[row["file_id"]].append(row["name"])
        return result

    def get_files_by_rating(self, rating: int) -> list[dict]:
        rows = self._fetchall(
            "SELECT * FROM files WHERE rating = ? ORDER BY date_modified DESC",
            (rating,),
        )
        return [dict(r) for r in rows]

    def get_files_by_color(self, color: str) -> list[dict]:
        rows = self._fetchall(
            "SELECT * FROM files WHERE color_label = ? ORDER BY date_modified DESC",
            (color.lower(),),
        )
        return [dict(r) for r in rows]

    # --- Backup / restore ---

    def backup_database(self, dest_path: Path) -> None:
        with self._lock:
            conn = self._connect()
            dest = sqlite3.connect(str(dest_path))
            conn.backup(dest)
            dest.close()

    def restore_database(self, source_path: Path) -> None:
        self.close()
        import shutil
        shutil.copy2(source_path, self._db_path)
        self._init_db()
