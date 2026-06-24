"""Application-wide constants."""

from pathlib import Path

APP_NAME = "CaptureVault"
APP_ID = "com.capturevault.app"

# Supported file extensions grouped by type
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
    ".heic", ".heif", ".svg", ".ico", ".psd",
}
RAW_EXTENSIONS = {
    ".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".rw2", ".pef",
    ".srw", ".raf", ".raw", ".3fr", ".erf", ".mef", ".mos", ".nrw",
    ".rwl", ".x3f",
}
VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".3gp", ".mts", ".m2ts",
}
AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".aiff",
}
DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp", ".rtf", ".txt", ".csv",
}
OTHER_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".json", ".xml", ".html", ".htm",
}

ALL_EXTENSIONS = (
    IMAGE_EXTENSIONS | RAW_EXTENSIONS | VIDEO_EXTENSIONS
    | AUDIO_EXTENSIONS | DOCUMENT_EXTENSIONS | OTHER_EXTENSIONS
)

# Photos only — used in Photographer Mode
PHOTOGRAPHER_EXTENSIONS = IMAGE_EXTENSIONS | RAW_EXTENSIONS

DEFAULT_SEARCH_FILTER = "images"
GENERAL_SEARCH_FILTER = "all"

FILE_TYPE_IMAGE = "image"
FILE_TYPE_RAW = "raw"
FILE_TYPE_VIDEO = "video"
FILE_TYPE_AUDIO = "audio"
FILE_TYPE_DOCUMENT = "document"
FILE_TYPE_OTHER = "other"

COLOR_LABELS = ("red", "yellow", "green", "blue", "purple")

DEFAULT_THUMBNAIL_SIZE = 128
MIN_THUMBNAIL_SIZE = 64
MAX_THUMBNAIL_SIZE = 256

THEME_LIGHT = "light"
THEME_DARK = "dark"

# GitHub update configuration (override via settings)
DEFAULT_GITHUB_REPO = "your-org/CaptureVault"

# Rating search patterns
RATING_QUERY_PREFIX = "rating:"
