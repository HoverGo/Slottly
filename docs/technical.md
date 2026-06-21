# Техническая документация

## Стек и версии

| Компонент | Технология |
|-----------|------------|
| Runtime | Python 3.12 |
| Web | FastAPI, Uvicorn |
| ORM | SQLAlchemy 2.0 async |
| DB | PostgreSQL 18 |
| Миграции | Alembic |
| Auth | JWT (python-jose), bcrypt |
| Validation | Pydantic v2 |
| Контейнеризация | Docker Compose |

## Структура `app/`

```
app/
├── main.py                 # FastAPI app, роутеры, lifespan
├── api/
│   ├── deps.py             # get_current_user, get_company_tenant, require_permission, require_platform_admin
│   └── routes/
│       ├── auth.py
│       ├── admin.py        # глобальная админ-панель
│       ├── cabinet.py
│       ├── companies.py
│       ├── payments.py
│       ├── permissions.py
│       └── schedules.py
├── core/
│   ├── config.py           # pydantic-settings
│   ├── database.py         # async engine, session
│   ├── security.py         # JWT, hash password
│   ├── tenant.py           # TenantContext
│   ├── permissions.py      # коды прав RBAC
│   └── exceptions.py       # AppError, NotFoundError, ForbiddenError, ConflictError
├── models/
│   ├── entities.py         # SQLAlchemy модели
│   └── enums.py            # PaymentAction, PaymentProvider
├── repositories/
│   └── tenant_repository.py
├── schemas/                # Pydantic request/response
└── services/               # бизнес-логика
    ├── auth_service.py
    ├── admin_service.py
    ├── company_service.py
    ├── subscription_service.py
    ├── user_subscription_service.py
    ├── payment_service.py
    ├── promo_service.py
    ├── join_request_service.py
    ├── member_service.py
    ├── schedule_service.py
    ├── seed_service.py
    └── payment_providers/
```

## Паттерны

### Async session

Эндпоинты получают сессию через `Depends(get_db)`. Commit выполняется в dependency после успешного ответа.

### Tenant-доступ

```python
tenant: TenantContext = Depends(get_company_tenant)                    # владелец или участник
tenant: TenantContext = Depends(require_permission(MANAGE_ROLES))    # + право RBAC
```

### Platform admin

```python
admin: User = Depends(require_platform_admin)  # is_platform_admin == True
```

### Обработка ошибок

Сервисы бросают `AppError` / `NotFoundError` / `ForbiddenError` / `ConflictError`.  
Глобальный handler в `main.py` → JSON `{ "detail": "..." }`.

### Enum в PostgreSQL

Миграции создают типы через `DO $$ ... EXCEPTION WHEN duplicate_object`, в колонках — `create_type=False`.

## Конфигурация

Файл `.env` в корне (не коммитить). Класс `Settings` в `app/core/config.py`.

Критичные переменные для prod:
- `SECRET_KEY`
- `DATABASE_URL`
- `PLATFORM_ADMIN_EMAILS`
- `PLATFORM_SUPPORT_EMAILS`

## API

- Префикс: `/api/v1`
- Auth: `Authorization: Bearer <token>`
- Login: `POST /auth/login`, form-data, поле `username` = email
- OpenAPI: `/docs`, `/redoc`

Полный справочник: [api-endpoints.md](api-endpoints.md).

## Локальная разработка без Docker

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Соглашения

- Комментарии в коде — на русском, без точки в конце
- Имена файлов — snake_case
- Новые эндпоинты — в `app/api/routes/`, логика в `app/services/`
- Данные компании — только через `TenantRepository` с `company_id`
