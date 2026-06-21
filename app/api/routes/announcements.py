from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.entities import User
from app.schemas.cabinet import PlatformAnnouncementPublicResponse
from app.services.announcement_service import list_active_announcements
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("", response_model=list[PlatformAnnouncementPublicResponse])
async def list_platform_announcements(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlatformAnnouncementPublicResponse]:
    items = await list_active_announcements(db)
    return [
        PlatformAnnouncementPublicResponse(
            id=item.id,
            title=item.title,
            message=item.message,
            maintenance_starts_at=item.maintenance_starts_at,
            maintenance_ends_at=item.maintenance_ends_at,
            created_at=item.created_at,
        )
        for item in items
    ]
