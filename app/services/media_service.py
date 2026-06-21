from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.core.permissions import MANAGE_COMPANY, MANAGE_MEMBERS
from app.core.tenant import TenantContext
from app.models.entities import Company, CompanyGalleryPhoto, CompanyMember
from app.repositories.tenant_repository import TenantRepository

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def media_url(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    prefix = settings.media_url_prefix.rstrip("/")
    return f"{prefix}/{relative_path.replace(chr(92), '/')}"


def public_media_url(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    return f"/api/v1/public/media/{relative_path.replace(chr(92), '/')}"


def upload_root() -> Path:
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def resolve_safe_path(relative_path: str) -> Path:
    root = upload_root()
    target = (root / relative_path).resolve()
    if not str(target).startswith(str(root)):
        raise AppError("Недопустимый путь к файлу")
    return target


def delete_file(relative_path: str | None) -> None:
    if not relative_path:
        return
    path = resolve_safe_path(relative_path)
    if path.is_file():
        path.unlink()


async def _read_and_validate_upload(file: UploadFile) -> tuple[bytes, str]:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise AppError("Допустимые форматы: JPEG, PNG, WebP")

    data = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise AppError(f"Размер файла не более {settings.max_upload_size_mb} МБ")
    if not data:
        raise AppError("Файл пустой")
    return data, ALLOWED_CONTENT_TYPES[content_type]


def _save_bytes(relative_path: str, data: bytes) -> str:
    path = resolve_safe_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return relative_path.replace("\\", "/")


MAX_GALLERY_PHOTOS = 20


def _can_manage_company_profile(tenant: TenantContext) -> bool:
    if tenant.is_owner:
        return True
    return tenant.has_permission(MANAGE_COMPANY) or tenant.has_permission(MANAGE_MEMBERS)


def _can_edit_member_photo(tenant: TenantContext, member: CompanyMember) -> bool:
    if _can_manage_company_profile(tenant):
        return True
    return tenant.member is not None and tenant.member.id == member.id


async def upload_company_photo(
    db: AsyncSession,
    tenant: TenantContext,
    file: UploadFile,
) -> Company:
    if not _can_manage_company_profile(tenant):
        raise ForbiddenError("Нет права на изменение логотипа компании")

    data, ext = await _read_and_validate_upload(file)
    relative = f"companies/{tenant.company_id}/logo.{ext}"
    delete_file(tenant.company.photo_path)
    _save_bytes(relative, data)
    tenant.company.photo_path = relative
    await db.flush()
    return tenant.company


async def delete_company_photo(db: AsyncSession, tenant: TenantContext) -> Company:
    if not _can_manage_company_profile(tenant):
        raise ForbiddenError("Нет права на изменение логотипа компании")

    delete_file(tenant.company.photo_path)
    tenant.company.photo_path = None
    await db.flush()
    return tenant.company


async def upload_company_gallery_photo(
    db: AsyncSession,
    tenant: TenantContext,
    file: UploadFile,
) -> CompanyGalleryPhoto:
    if not _can_manage_company_profile(tenant):
        raise ForbiddenError("Нет права на изменение фото студии")

    repo = TenantRepository(db, tenant.company_id)
    count = await repo.count_gallery_photos()
    if count >= MAX_GALLERY_PHOTOS:
        raise AppError(f"Не более {MAX_GALLERY_PHOTOS} фото в галерее")

    data, ext = await _read_and_validate_upload(file)
    photo_id = uuid4()
    relative = f"companies/{tenant.company_id}/gallery/{photo_id}.{ext}"
    _save_bytes(relative, data)

    photo = CompanyGalleryPhoto(
        id=photo_id,
        company_id=tenant.company_id,
        path=relative,
        sort_order=count,
    )
    db.add(photo)
    await db.flush()
    return photo


async def delete_company_gallery_photo(
    db: AsyncSession,
    tenant: TenantContext,
    photo_id: UUID,
) -> None:
    if not _can_manage_company_profile(tenant):
        raise ForbiddenError("Нет права на изменение фото студии")

    repo = TenantRepository(db, tenant.company_id)
    photo = await repo.get_gallery_photo(photo_id)
    if not photo:
        raise NotFoundError("Фото не найдено")

    delete_file(photo.path)
    await db.delete(photo)
    await db.flush()


async def upload_member_photo(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
    file: UploadFile,
) -> CompanyMember:
    repo = TenantRepository(db, tenant.company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден")

    if not _can_edit_member_photo(tenant, member):
        raise ForbiddenError("Нет права на изменение фото сотрудника")

    data, ext = await _read_and_validate_upload(file)
    relative = f"companies/{tenant.company_id}/members/{member.id}.{ext}"
    delete_file(member.photo_path)
    _save_bytes(relative, data)
    member.photo_path = relative
    await db.flush()
    return member


async def delete_member_photo(
    db: AsyncSession,
    tenant: TenantContext,
    member_id: UUID,
) -> CompanyMember:
    repo = TenantRepository(db, tenant.company_id)
    member = await repo.get_member_by_id(member_id)
    if not member:
        raise NotFoundError("Сотрудник не найден")

    if not _can_edit_member_photo(tenant, member):
        raise ForbiddenError("Нет права на изменение фото сотрудника")

    delete_file(member.photo_path)
    member.photo_path = None
    await db.flush()
    return member


def parse_media_company_id(relative_path: str) -> UUID | None:
    parts = relative_path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "companies":
        try:
            return UUID(parts[1])
        except ValueError:
            return None
    return None


async def user_can_access_media(
    db: AsyncSession,
    user_id: UUID,
    relative_path: str,
) -> bool:
    company_id = parse_media_company_id(relative_path)
    if not company_id:
        return False

    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        return False
    if company.owner_id == user_id:
        return True

    repo = TenantRepository(db, company_id)
    return await repo.get_member_by_user_id(user_id) is not None


async def company_allows_public_media(db: AsyncSession, relative_path: str) -> bool:
    company_id = parse_media_company_id(relative_path)
    if not company_id:
        return False
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    return company is not None and company.public_booking_enabled


def content_type_for_path(relative_path: str) -> str:
    ext = relative_path.rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(ext, "application/octet-stream")
