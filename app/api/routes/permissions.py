from fastapi import APIRouter

from app.core.permissions import ALL_PERMISSIONS, PERMISSION_LABELS

router = APIRouter(tags=["permissions"])


@router.get("/permissions")
async def list_permissions() -> list[dict[str, str]]:
    return [{"code": code, "label": PERMISSION_LABELS[code]} for code in sorted(ALL_PERMISSIONS)]
