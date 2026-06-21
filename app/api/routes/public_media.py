from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppError
from app.services.media_service import (
    company_allows_public_media,
    content_type_for_path,
    resolve_safe_path,
)

router = APIRouter(prefix="/public/media", tags=["public-media"])


@router.get("/{relative_path:path}")
async def get_public_media_file(
    relative_path: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    try:
        if not await company_allows_public_media(db, relative_path):
            raise AppError("Файл не найден", status_code=404)

        path = resolve_safe_path(relative_path)
        if not path.is_file():
            raise AppError("Файл не найден", status_code=404)

        return FileResponse(path, media_type=content_type_for_path(relative_path))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
