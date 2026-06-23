"""Thumbnail generation and caching."""

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from capturevault.constants import (
    FILE_TYPE_AUDIO,
    FILE_TYPE_DOCUMENT,
    FILE_TYPE_IMAGE,
    FILE_TYPE_RAW,
    FILE_TYPE_VIDEO,
    IMAGE_EXTENSIONS,
)


class ThumbnailService:
    """Generate and cache thumbnails without modifying source files."""

    def __init__(self, cache_dir: Path, size: int = 128) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._size = size

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        self._size = value

    def _cache_key(self, file_path: str, size: int) -> Path:
        digest = hashlib.md5(f"{file_path}:{size}".encode()).hexdigest()
        return self._cache_dir / f"{digest}.jpg"

    def get_thumbnail_path(self, file_path: str, file_type: str, extension: str) -> Path:
        """Return cached thumbnail path, generating if needed."""
        cache_path = self._cache_key(file_path, self._size)
        if cache_path.exists():
            return cache_path

        path = Path(file_path)
        if not path.exists():
            return self._create_placeholder(file_type, extension, cache_path)

        ext = extension.lower()
        try:
            if ext in IMAGE_EXTENSIONS or file_type in (FILE_TYPE_IMAGE, FILE_TYPE_RAW):
                self._generate_image_thumbnail(path, cache_path)
            else:
                self._create_placeholder(file_type, extension, cache_path)
        except (OSError, IOError, Image.UnidentifiedImageError):
            self._create_placeholder(file_type, extension, cache_path)

        return cache_path

    def _generate_image_thumbnail(self, source: Path, dest: Path) -> None:
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail((self._size, self._size), Image.Resampling.LANCZOS)
            img.save(dest, "JPEG", quality=85)

    def _create_placeholder(
        self, file_type: str, extension: str, dest: Path
    ) -> Path:
        size = self._size
        img = Image.new("RGB", (size, size), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        label = self._type_label(file_type, extension)
        try:
            font = ImageFont.truetype("arial.ttf", max(12, size // 8))
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            ((size - tw) / 2, (size - th) / 2),
            label,
            fill=(100, 100, 100),
            font=font,
        )
        img.save(dest, "JPEG", quality=85)
        return dest

    @staticmethod
    def _type_label(file_type: str, extension: str) -> str:
        labels = {
            FILE_TYPE_VIDEO: "VIDEO",
            FILE_TYPE_AUDIO: "AUDIO",
            FILE_TYPE_DOCUMENT: "DOC",
            FILE_TYPE_RAW: "RAW",
        }
        if file_type in labels:
            return labels[file_type]
        ext = extension.lstrip(".").upper()
        return ext[:6] if ext else "FILE"

    def clear_cache(self) -> None:
        for f in self._cache_dir.glob("*.jpg"):
            try:
                f.unlink()
            except OSError:
                pass
