import pytest

from app.core.exceptions import AppError
from app.core.upload_validation import validate_image_upload

# Минимальный валидный PNG 1x1
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\x0d\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_validate_png():
    ext = validate_image_upload(TINY_PNG, "image/png")
    assert ext == "png"


def test_reject_mismatch_content_type():
    with pytest.raises(AppError, match="не совпадает"):
        validate_image_upload(TINY_PNG, "image/jpeg")


def test_reject_non_image():
    with pytest.raises(AppError, match="допустимым"):
        validate_image_upload(b"not an image at all", "image/png")
