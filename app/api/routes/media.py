from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.entities import User
from app.services.media_service import (
    content_type_for_path,
    resolve_safe_path,
    user_can_access_media,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{relative_path:path}")
async def get_media_file(
    relative_path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    try:
        if not await user_can_access_media(db, current_user.id, relative_path):
            raise AppError("Файл не найден", status_code=404)

        path = resolve_safe_path(relative_path)
        if not path.is_file():
            raise AppError("Файл не найден", status_code=404)

        return FileResponse(path, media_type=content_type_for_path(relative_path))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
