from app.models.entities import User


def user_is_platform_staff(user: User) -> bool:
    return user.is_platform_admin or user.is_platform_support or user.is_platform_main_admin


def user_can_manage_company_offers(user: User) -> bool:
    return user.is_platform_admin or user.is_platform_main_admin
