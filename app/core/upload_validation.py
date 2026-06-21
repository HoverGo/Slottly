"""Проверка содержимого загружаемых изображений по magic bytes"""

from app.core.exceptions import AppError

ALLOWED_IMAGE_EXTENSIONS = frozenset({"jpeg", "png", "webp"})

CONTENT_TYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def detect_image_kind(data: bytes) -> str | None:
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    return None


def validate_image_upload(data: bytes, content_type: str) -> str:
    normalized_type = (content_type or "").lower()
    if normalized_type not in CONTENT_TYPE_TO_EXT:
        raise AppError("Допустимые форматы: JPEG, PNG, WebP")

    kind = detect_image_kind(data)
    if kind not in ALLOWED_IMAGE_EXTENSIONS:
        raise AppError("Файл не является допустимым изображением")

    expected_ext = CONTENT_TYPE_TO_EXT[normalized_type]
    if kind == "jpeg" and expected_ext == "jpg":
        return "jpg"
    if kind == "webp" and expected_ext == "webp":
        return "webp"
    if kind == expected_ext or (kind == "jpeg" and expected_ext == "jpg"):
        return expected_ext
    raise AppError("Тип файла не совпадает с содержимым")
