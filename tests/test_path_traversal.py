import pytest

from app.core.exceptions import AppError
from app.services.media_service import resolve_safe_path, upload_root


def test_resolve_safe_path_blocks_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.media_service.settings.upload_dir", str(tmp_path))
    with pytest.raises(AppError, match="Недопустимый"):
        resolve_safe_path("../../etc/passwd")


def test_resolve_safe_path_allows_valid_path(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.media_service.settings.upload_dir", str(tmp_path))
    path = resolve_safe_path("companies/test.jpg")
    assert str(path).startswith(str(upload_root()))
