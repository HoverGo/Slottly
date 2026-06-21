"""Коды прав роли в компании. Владелец компании имеет все права автоматически"""

MANAGE_ROLES = "manage_roles"
MANAGE_MEMBERS = "manage_members"
MANAGE_BRANCHES = "manage_branches"
MANAGE_SCHEDULES = "manage_schedules"
MANAGE_JOIN_REQUESTS = "manage_join_requests"
MANAGE_SERVICES = "manage_services"
MANAGE_COMPANY = "manage_company"
MANAGE_WAREHOUSE = "manage_warehouse"
VIEW_STATISTICS = "view_statistics"

ALL_PERMISSIONS: frozenset[str] = frozenset(
    {
        MANAGE_ROLES,
        MANAGE_MEMBERS,
        MANAGE_BRANCHES,
        MANAGE_SCHEDULES,
        MANAGE_JOIN_REQUESTS,
        MANAGE_SERVICES,
        MANAGE_COMPANY,
        MANAGE_WAREHOUSE,
        VIEW_STATISTICS,
    }
)

PERMISSION_LABELS: dict[str, str] = {
    MANAGE_ROLES: "Управление ролями и правами",
    MANAGE_MEMBERS: "Управление сотрудниками (смена ролей)",
    MANAGE_BRANCHES: "Управление филиалами",
    MANAGE_SCHEDULES: "Настройка расписания записей",
    MANAGE_JOIN_REQUESTS: "Приглашения в компанию",
    MANAGE_SERVICES: "Управление услугами и записями клиентов",
    MANAGE_COMPANY: "Редактирование профиля компании",
    MANAGE_WAREHOUSE: "Управление складом и движением товаров",
    VIEW_STATISTICS: "Просмотр статистики и дашборда",
}
