# Commerce Booking API

Бэкенд системы записи: мультикомпании, RBAC, подписки, платежи, расписание слотов, глобальная админ-панель.

## Стек

- FastAPI + Uvicorn
- SQLAlchemy 2.0 (async) + PostgreSQL 18
- Alembic
- JWT (Bearer)
- Docker Compose

## Быстрый старт

```bash
docker compose up --build
```

| URL | Назначение |
|-----|------------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Healthcheck |

При старте контейнер `api`:
1. Ждёт PostgreSQL
2. Применяет миграции Alembic (`001`–`024`)
3. Сидирует тарифы и назначает platform-admin по email
4. Запускает Uvicorn

### Режим разработки (hot-reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Остановка

```bash
docker compose down        # остановить
docker compose down -v     # остановить и удалить данные БД/Redis
```

При обновлении с PostgreSQL 16 на 18 путь тома БД изменился — для миграции данных используйте `pg_dump`/`pg_restore` или пересоздайте том (`down -v`).

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `SECRET_KEY` | см. compose | Ключ JWT (в production ≥ 32 символов) |
| `ENVIRONMENT` | `development` | `production` включает проверку конфигурации |
| `DATABASE_URL` | `...@db:5432/commerce_db` | PostgreSQL |
| `DEBUG` | `false` | Лог SQL, OpenAPI |
| `PAYMENT_WEBHOOK_SECRET` | — | Секрет webhook (`X-Webhook-Secret`) |
| `CORS_ORIGINS` | — | Разрешённые origin через запятую |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Время жизни токена |
| `PAYMENT_PROVIDER` | `mock` | `mock`, `yookassa`, `cloudpayments` |
| `PAYMENT_RETURN_URL` | `http://localhost:8000/cabinet/payments/success` | URL возврата после оплаты |
| `PLATFORM_ADMIN_EMAILS` | — | Email админов через запятую (права выдаются при старте) |
| `PLATFORM_SUPPORT_EMAILS` | — | Email техподдержки через запятую (права выдаются при старте) |
| `WEB_CONCURRENCY` | `1` | Число воркеров Uvicorn |

Пример `.env`:

```bash
SECRET_KEY=your-secret-key
PLATFORM_ADMIN_EMAILS=admin@example.com
PLATFORM_SUPPORT_EMAILS=support@example.com
PAYMENT_PROVIDER=mock
```

## Бизнес-правила

### Подписки

- При регистрации выдаётся **бесплатный тариф `basic`**: 3 сотрудника, 5 услуг, 50 записей в месяц
- Одна **подписка** (`UserSubscription`) = один слот на **одну компанию**
- Лимиты тарифа: `max_users`, `max_branches`, `max_roles`, `max_services`, `max_appointments_per_month`
- Покупка: `POST /payments/checkout` с `action: "purchase"`
- Компания создаётся с привязкой свободной подписки: `POST /companies { subscription_id }`
- Периоды оплаты: **1, 3, 6, 12** месяцев
- Цена = `price_monthly × period_months` (скидка промокодом уменьшает итог)
- Истечение подписки блокирует операции компании до продления

### Действия оплаты

| action | Описание |
|--------|----------|
| `purchase` | Новый слот подписки |
| `renew` | Продление |
| `change_plan` | Смена тарифа (апгрейд сразу, даунгрейд со след. периода) |

### Лимиты компании

Задаются тарифом: `max_users`, `max_branches`, `max_roles`. Проверяются перед созданием ролей, филиалов, приглашений.

### Сотрудники

- Добавление только через **приглашения** (`join-requests`), прямого `POST /members` нет
- Сотрудник принимает приглашение в личном кабинете

### RBAC

Права на роли (`permissions` JSONB): `manage_roles`, `manage_members`, `manage_branches`, `manage_schedules`, `manage_join_requests`, `manage_services`. Владелец имеет все права.

### Расписание

- Базовое расписание: паттерны `weekly`, `cycle`, `manual`
- **Исключения**: выходной или блокировка слотов; даты — день, диапазон (до 365 дней) или список `dates`
- Управление: `manage_schedules` или владелец

### Промокоды

- Создаются в глобальной админ-панели
- Персональные (на пользователя) или для всех
- Предпросмотр скидки: `POST /payments/checkout/preview` перед оплатой

### Техподдержка

- Пользователь: `POST /support/tickets`, переписка в своих обращениях
- Сотрудник support (`is_platform_support`) или админ: `/admin/support/*` — все тикеты, ответы, смена статуса и назначение
- Назначение роли: `PLATFORM_SUPPORT_EMAILS` или `PATCH /admin/users/{id}/platform-support` (админ)

### Услуги и записи

- Каталог услуг с длительностью (`duration_minutes`): право `manage_services` или владелец
- Запись клиента на услугу блокирует пересекающиеся слоты в расписании
- Свободные слоты: `GET .../schedules/{id}/slots?service_id=...` — с учётом длительности услуги

### Фото

- **Онлайн-запись:** `PATCH /companies/{id}` с `public_booking_enabled: true` → поле `booking_url`; публичное API `/public/booking/{slug}` (без JWT)
- **Профиль компании:** `PATCH /companies/{id}` — название, адрес, телефон, тип организации, график работы
- **Логотип:** `POST/DELETE /companies/{id}/logo` (или `/photo`) — владелец, `manage_company` или `manage_members`
- **Галерея студии:** `POST/DELETE /companies/{id}/gallery` — до 20 фото
- **Сотрудник:** `POST/DELETE /companies/{id}/members/{member_id}/photo` — сам сотрудник или менеджер/владелец
- Просмотр: `GET /api/v1/media/{path}` с JWT (участники компании)
- Форматы: JPEG, PNG, WebP, до 5 МБ

### Изоляция компаний

- Все данные компании через `TenantRepository` + `company_id`
- Чужая компания → **404** (не 403)
- Составной FK: роль привязана только к своей компании

## Тарифы по умолчанию

| code | Лимиты (users / branches / roles) | Услуги / записи в мес | ₽/мес |
|------|-----------------------------------|-------|
| `starter` | 10 / 3 / 5 | 20 услуг, 500 записей/мес | 990 |
| `business` | 50 / 10 / 20 | 100 услуг, 3000 записей/мес | 2990 |
| `enterprise` | 200 / 50 / 100 | 500 услуг, 20000 записей/мес | 9990 |
| `basic` | 3 / 1 / 3 | 5 услуг, 50 записей/мес | 0 (при регистрации) |

## Документация

| Файл | Содержание |
|------|------------|
| [docs/api-endpoints.md](docs/api-endpoints.md) | Справочник API с примерами JSON |
| [docs/architecture.md](docs/architecture.md) | Архитектура, сущности, потоки |
| [docs/technical.md](docs/technical.md) | Стек, структура кода, паттерны |
| [docs/faq.md](docs/faq.md) | Частые вопросы и ответы |
| [docs/legal/](docs/legal/) | Пользовательское соглашение, политики |

## Структура проекта

```
app/
  api/routes/       # auth, admin, admin_support, support, services, cabinet, companies, payments, permissions, schedules
  core/             # config, database, security, tenant, permissions, exceptions
  models/           # SQLAlchemy-сущности
  repositories/     # TenantRepository
  schemas/          # Pydantic-модели
  services/         # бизнес-логика, payment_providers/
alembic/versions/   # миграции 001–013
scripts/            # docker_entrypoint.py
docs/
```

## Типичный сценарий владельца

```
1. POST /auth/register → POST /auth/login
2. POST /payments/checkout/preview   (опционально: промокод)
3. POST /payments/checkout           { action: "purchase", plan_code, period_months }
4. GET  /cabinet                     → subscription_id
5. POST /companies                   { name, subscription_id }
6. POST /companies/{id}/roles
7. POST /companies/{id}/join-requests
8. POST /companies/{id}/members/{id}/schedules
```

## Безопасность

Реализовано в коде:

| Механизм | Описание |
|----------|----------|
| Rate limiting | По IP и типу endpoint; **Redis** при `REDIS_URL` — общий счётчик для нескольких воркеров |
| Anti-bruteforce | Блокировка входа после `LOGIN_MAX_ATTEMPTS`; **Redis** при `REDIS_URL` |
| Audit log | Журнал действий в БД: auth, мутации API, админка; `GET /admin/audit-logs` |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS в production |
| CORS | Настраивается через `CORS_ORIGINS` |
| Webhook secret | `X-Webhook-Secret` для `/payments/webhook/*`; mock запрещён в production |
| Upload validation | Magic bytes + проверка соответствия Content-Type |
| Path traversal | Блокировка `../` при доступе к файлам |
| Пароли | bcrypt; мин. 8 символов, буква + цифра |
| Production config | Валидация `SECRET_KEY`, БД, webhook при `ENVIRONMENT=production` |
| Tenant isolation | Чужая компания → 404 |
| PII | Хранится в БД; HTTPS обязателен в production (reverse proxy) |

Подробнее: `docs/legal/security-policy.md`, переменные — `.env.example`.

### Автотесты

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

Покрытие: rate limit, brute-force, audit, webhook, upload, path traversal, JWT/пароли, middleware, production config.

## Админ платформы

Пользователь с `is_platform_admin: true` получает доступ к `/api/v1/admin/*`: дашборд, пользователи, компании (с подписками и оплатой), объявления о техработах, промокоды, журнал аудита, назначение роли техподдержки.

## Техподдержка платформы

Пользователь с `is_platform_support: true` (через `PLATFORM_SUPPORT_EMAILS` или API от админа) работает с обращениями в `/api/v1/admin/support/*`. Админы имеют те же права на тикеты плюс полный доступ к админке.
