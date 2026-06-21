import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.entities import Company

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


def normalize_booking_slug(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise AppError("Некорректная ссылка для записи")
    if len(slug) > 64:
        slug = slug[:64].rstrip("-")
    if not SLUG_PATTERN.match(slug):
        raise AppError("Ссылка может содержать только латинские буквы, цифры и дефис")
    return slug


def slug_from_company_name(name: str) -> str:
    translit_map = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
    chars = []
    for ch in name.strip().lower():
        if ch in translit_map:
            chars.append(translit_map[ch])
        else:
            chars.append(ch)
    return normalize_booking_slug("".join(chars))


async def ensure_unique_booking_slug(
    db: AsyncSession,
    slug: str,
    *,
    exclude_company_id: UUID | None = None,
) -> str:
    base = normalize_booking_slug(slug)
    candidate = base
    suffix = 1
    while True:
        query = select(Company.id).where(Company.booking_slug == candidate)
        if exclude_company_id is not None:
            query = query.where(Company.id != exclude_company_id)
        existing = await db.scalar(query)
        if not existing:
            return candidate
        suffix += 1
        candidate = normalize_booking_slug(f"{base}-{suffix}")


async def validate_booking_slug_available(
    db: AsyncSession,
    slug: str,
    *,
    exclude_company_id: UUID | None = None,
) -> str:
    normalized = normalize_booking_slug(slug)
    query = select(Company.id).where(Company.booking_slug == normalized)
    if exclude_company_id is not None:
        query = query.where(Company.id != exclude_company_id)
    existing = await db.scalar(query)
    if existing:
        raise ConflictError("Ссылка для онлайн-записи уже занята")
    return normalized


def booking_page_url(slug: str) -> str:
    return f"{settings.public_booking_base_url.rstrip('/')}/{slug}"
