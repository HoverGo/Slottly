from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, NotFoundError
from app.models.entities import PlatformAnnouncement, User


async def create_announcement(
    db: AsyncSession,
    admin: User,
    *,
    title: str,
    message: str,
    maintenance_starts_at: datetime | None = None,
    maintenance_ends_at: datetime | None = None,
) -> PlatformAnnouncement:
    if maintenance_starts_at and maintenance_ends_at and maintenance_ends_at < maintenance_starts_at:
        raise AppError("maintenance_ends_at не может быть раньше maintenance_starts_at")

    announcement = PlatformAnnouncement(
        title=title,
        message=message,
        maintenance_starts_at=maintenance_starts_at,
        maintenance_ends_at=maintenance_ends_at,
        is_active=True,
        created_by_id=admin.id,
    )
    db.add(announcement)
    await db.flush()
    return announcement


async def list_announcements_admin(db: AsyncSession) -> list[PlatformAnnouncement]:
    result = await db.execute(
        select(PlatformAnnouncement)
        .options(selectinload(PlatformAnnouncement.created_by))
        .order_by(PlatformAnnouncement.created_at.desc())
    )
    return list(result.scalars().all())


async def list_active_announcements(db: AsyncSession) -> list[PlatformAnnouncement]:
    now = datetime.now(UTC)
    result = await db.execute(
        select(PlatformAnnouncement)
        .where(PlatformAnnouncement.is_active.is_(True))
        .order_by(PlatformAnnouncement.created_at.desc())
    )
    announcements = list(result.scalars().all())
    visible: list[PlatformAnnouncement] = []
    for item in announcements:
        if item.maintenance_ends_at and item.maintenance_ends_at <= now:
            continue
        if item.maintenance_starts_at and item.maintenance_starts_at > now:
            continue
        visible.append(item)
    return visible


async def update_announcement(
    db: AsyncSession,
    announcement_id: UUID,
    *,
    title: str | None = None,
    message: str | None = None,
    maintenance_starts_at: datetime | None = None,
    maintenance_ends_at: datetime | None = None,
    is_active: bool | None = None,
    clear_maintenance_starts_at: bool = False,
    clear_maintenance_ends_at: bool = False,
) -> PlatformAnnouncement:
    announcement = await db.get(PlatformAnnouncement, announcement_id)
    if not announcement:
        raise NotFoundError("Объявление не найдено")

    if title is not None:
        announcement.title = title
    if message is not None:
        announcement.message = message
    if clear_maintenance_starts_at:
        announcement.maintenance_starts_at = None
    elif maintenance_starts_at is not None:
        announcement.maintenance_starts_at = maintenance_starts_at
    if clear_maintenance_ends_at:
        announcement.maintenance_ends_at = None
    elif maintenance_ends_at is not None:
        announcement.maintenance_ends_at = maintenance_ends_at
    if is_active is not None:
        announcement.is_active = is_active

    starts = announcement.maintenance_starts_at
    ends = announcement.maintenance_ends_at
    if starts and ends and ends < starts:
        raise AppError("maintenance_ends_at не может быть раньше maintenance_starts_at")

    await db.flush()
    return announcement
