"""Search filter options for type and folder scope."""

from dataclasses import dataclass

from capturevault.constants import (
    DOCUMENT_EXTENSIONS,
    FILE_TYPE_AUDIO,
    FILE_TYPE_DOCUMENT,
    FILE_TYPE_IMAGE,
    FILE_TYPE_RAW,
    FILE_TYPE_VIDEO,
)

WORD_EXTENSIONS = frozenset({".doc", ".docx", ".odt", ".rtf"})

# (label, filter key)
TYPE_FILTER_OPTIONS: list[tuple[str, str]] = [
    ("All file types", "all"),
    ("Images", "images"),
    ("RAW photos", "raw"),
    ("Videos", "videos"),
    ("PDF only", "pdf"),
    ("Word (.doc/.docx)", "word"),
    ("Documents", "documents"),
    ("Audio", "audio"),
]

TYPE_TO_FILE_TYPES: dict[str, tuple[str, ...]] = {
    "images": (FILE_TYPE_IMAGE, FILE_TYPE_RAW),
    "raw": (FILE_TYPE_RAW,),
    "videos": (FILE_TYPE_VIDEO,),
    "documents": (FILE_TYPE_DOCUMENT,),
    "audio": (FILE_TYPE_AUDIO,),
}

TYPE_TO_EXTENSIONS: dict[str, frozenset[str]] = {
    "pdf": frozenset({".pdf"}),
    "word": WORD_EXTENSIONS,
    "documents": DOCUMENT_EXTENSIONS,
}


@dataclass
class SearchFilters:
    """UI-selected search scope."""

    type_filter: str = "all"
    folder_path: str | None = None

    def file_types(self) -> tuple[str, ...] | None:
        if self.type_filter in TYPE_TO_FILE_TYPES:
            return TYPE_TO_FILE_TYPES[self.type_filter]
        return None

    def extensions(self) -> frozenset[str] | None:
        return TYPE_TO_EXTENSIONS.get(self.type_filter)

    def extension(self) -> str | None:
        exts = self.extensions()
        if exts and len(exts) == 1:
            return next(iter(exts))
        return None

    def type_label(self) -> str:
        for label, key in TYPE_FILTER_OPTIONS:
            if key == self.type_filter:
                return label
        return "All file types"

    def folder_label(self) -> str:
        if not self.folder_path:
            return "All folders"
        p = self.folder_path
        if len(p) > 45:
            return "..." + p[-42:]
        return p

    def matches_file(self, file_data: dict) -> bool:
        if self.folder_path:
            if not _path_in_folder(file_data.get("path") or "", self.folder_path):
                return False

        exts = self.extensions()
        if exts:
            file_ext = (file_data.get("extension") or "").lower()
            return file_ext in exts

        types = self.file_types()
        if types:
            file_ext = (file_data.get("extension") or "").lower()
            if file_ext in DOCUMENT_EXTENSIONS and FILE_TYPE_DOCUMENT in types:
                return True
            return file_data.get("file_type") in types

        return True


def _path_in_folder(file_path: str, folder_path: str) -> bool:
    """True if file_path is inside folder_path (handles D: vs D:/ vs D:\\)."""
    path = file_path.replace("/", "\\").lower()
    folder = folder_path.replace("/", "\\").rstrip("\\").lower()
    if len(folder) == 2 and folder[1] == ":":
        # Drive root e.g. D:
        return path.startswith(folder + "\\") or path.startswith(folder)
    return path.startswith(folder + "\\") or path == folder
