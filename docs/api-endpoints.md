# Справочник API-эндпоинтов

Базовый URL: `http://localhost:8000`

Интерактивная документация: `/docs`

## Авторизация

Для защищённых эндпоинтов:

```
Authorization: Bearer <access_token>
```

Токен получается через `POST /api/v1/auth/login`.

---

## Сводка эндпоинтов

| Группа | Префикс | Auth |
|--------|---------|------|
| Система | `/health` | — |
| Auth | `/api/v1/auth` | частично |
| Права | `/api/v1/permissions` | — |
| Кабинет | `/api/v1/cabinet` | JWT |
| Платежи | `/api/v1/payments`, `/subscription-plans` | JWT / — |
| Компании | `/api/v1/companies` | JWT + tenant |
| Расписание | `/api/v1/companies/{id}/members/{id}/...` | JWT + tenant |
| Админ | `/api/v1/admin` | JWT + platform admin |
| Support (пользователь) | `/api/v1/support` | JWT |
| Support (staff) | `/api/v1/admin/support` | JWT + platform staff |
| Услуги | `/api/v1/companies/{id}/services` | JWT + tenant |
| Записи | `/api/v1/companies/{id}/members/{id}/appointments` | JWT + tenant |

---

## Система

### `GET /health`

Проверка работоспособности. Авторизация не требуется.

**Ответ `200`:**

```json
{ "status": "ok" }
```

---

## Аутентификация — `/api/v1/auth`

### `POST /api/v1/auth/register`

Регистрация пользователя.

**Запрос:**

```json
{
  "email": "ivan@example.com",
  "password": "securepass123",
  "full_name": "Иван Петров"
}
```

**Ответ `201`:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "ivan@example.com",
  "full_name": "Иван Петров",
  "is_active": true,
  "is_platform_admin": false,
  "created_at": "2026-06-17T12:00:00+00:00"
}
```

---

### `POST /api/v1/auth/login`

Вход. Возвращает JWT.

**Запрос** `application/x-www-form-urlencoded`:

| Поле | Значение |
|------|----------|
| `username` | email |
| `password` | пароль |

**Ответ `200`:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### `GET /api/v1/auth/me`

Текущий пользователь. Требуется JWT.

**Ответ `200`:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "ivan@example.com",
  "full_name": "Иван Петров",
  "is_active": true,
  "is_platform_admin": false,
  "created_at": "2026-06-17T12:00:00+00:00"
}
```

Поле `is_platform_admin` — доступ к `/api/v1/admin/*`.

---

### `POST /api/v1/auth/change-password`

Смена пароля. Требуется JWT.

**Запрос:**

```json
{
  "current_password": "securepass123",
  "new_password": "newsecurepass456"
}
```

**Ответ `204`:** без тела.

---

## Права — `/api/v1/permissions`

### `GET /api/v1/permissions`

Список доступных прав для ролей компании. Авторизация не требуется.

**Ответ `200`:**

```json
[
  { "code": "manage_branches", "label": "Управление филиалами" },
  { "code": "manage_join_requests", "label": "Приглашения в компанию" },
  { "code": "manage_members", "label": "Управление сотрудниками (смена ролей)" },
  { "code": "manage_roles", "label": "Управление ролями и правами" },
  { "code": "manage_schedules", "label": "Настройка расписания записей" },
  { "code": "manage_services", "label": "Управление услугами и записями клиентов" }
]
```

Владелец компании имеет все права автоматически.

---

## Личный кабинет — `/api/v1/cabinet`

### `GET /api/v1/cabinet`

Обзор личного кабинета. Требуется JWT.

**Ответ `200`:**

```json
{
  "user": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "ivan@example.com",
    "full_name": "Иван Петров",
    "is_active": true,
    "created_at": "2026-06-17T12:00:00+00:00"
  },
  "can_create_company": true,
  "available_subscription_slots": 1,
  "subscriptions": [
    {
      "id": "s1s1s1s1-s1s1-s1s1-s1s1-s1s1s1s1s1s1",
      "plan_id": "p1p1p1p1-p1p1-p1p1-p1p1-p1p1p1p1p1p1",
      "company_id": null,
      "status": "active",
      "started_at": "2026-06-17T12:00:00+00:00",
      "expires_at": "2026-09-17T12:00:00+00:00",
      "scheduled_plan_id": null,
      "scheduled_change_at": null,
      "is_available_for_company": true,
      "plan": {
        "id": "p1p1p1p1-p1p1-p1p1-p1p1-p1p1p1p1p1p1",
        "code": "starter",
        "name": "Стартовый",
        "description": "До 10 сотрудников, 3 филиала, 5 ролей",
        "max_users": 10,
        "max_branches": 3,
        "max_roles": 5,
        "price_monthly": 990
      },
      "scheduled_plan": null
    }
  ],
  "companies": [],
  "pending_join_requests": []
}
```

---

### `GET /api/v1/cabinet/join-requests`

Входящие приглашения в компании. Требуется JWT.

**Ответ `200`:** массив `JoinRequestResponse` (см. ниже).

---

### `POST /api/v1/cabinet/join-requests/{request_id}/accept`

Принять приглашение. Требуется JWT.

**Ответ `201`:**

```json
{
  "member_id": "m1m1m1m1-m1m1-m1m1-m1m1-m1m1m1m1m1m1",
  "company_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1"
}
```

---

### `POST /api/v1/cabinet/join-requests/{request_id}/reject`

Отклонить приглашение. Требуется JWT.

**Ответ `200`:** объект `JoinRequestResponse` со статусом `rejected`.

---

## Подписки и платежи

### `GET /api/v1/subscription-plans`

Список тарифов. Авторизация не требуется.

**Ответ `200`:**

```json
[
  {
    "id": "11111111-1111-1111-1111-111111111111",
    "code": "starter",
    "name": "Стартовый",
    "description": "До 10 сотрудников, 3 филиала, 5 ролей",
    "max_users": 10,
    "max_branches": 3,
    "max_roles": 5,
    "price_monthly": 990
  },
  {
    "id": "22222222-2222-2222-2222-222222222222",
    "code": "business",
    "name": "Бизнес",
    "description": "До 50 сотрудников, 10 филиалов, 20 ролей",
    "max_users": 50,
    "max_branches": 10,
    "max_roles": 20,
    "price_monthly": 2990
  }
]
```

---

### `GET /api/v1/companies/{company_id}/subscription/available-plans`

Тарифы, доступные для смены с учётом текущего использования. Только владелец. Требуется JWT.

**Ответ `200`:** массив `SubscriptionPlanResponse`.

---

### `POST /api/v1/payments/checkout/preview`

Предпросмотр оплаты **до нажатия «Оплатить»**: расчёт суммы и проверка промокода без создания платежа. Требуется JWT.

**Запрос** (те же поля, что у checkout):

```json
{
  "plan_code": "starter",
  "action": "purchase",
  "period_months": 3,
  "promo_code": "SUMMER20"
}
```

**Ответ `200` — промокод применён:**

```json
{
  "plan": {
    "code": "starter",
    "name": "Стартовый",
    "price_monthly": 990,
    "max_users": 10,
    "max_branches": 3,
    "max_roles": 5
  },
  "action": "purchase",
  "period_months": 3,
  "original_amount": 2970,
  "discount_amount": 594,
  "amount": 2376,
  "currency": "RUB",
  "promo_code": "SUMMER20",
  "promo_applied": true,
  "promo_error": null
}
```

**Ответ `200` — промокод невалиден** (сумма без скидки):

```json
{
  "original_amount": 2970,
  "discount_amount": 0,
  "amount": 2970,
  "promo_applied": false,
  "promo_error": "Промокод не найден"
}
```

---

### `POST /api/v1/payments/checkout`

Создание платежа. Требуется JWT.

**Действия (`action`):**

| action | Описание | `subscription_id` |
|--------|----------|-------------------|
| `purchase` | Новая подписка (слот на компанию) | не нужен |
| `renew` | Продление подписки | обязателен |
| `change_plan` | Смена тарифа (апгрейд сразу, даунгрейд со след. периода) | обязателен |

**Период:** `period_months` — `1`, `3`, `6` или `12`.

**Промокод:** опциональное поле `promo_code` (должен быть валиден, иначе `400`).

**Запрос — покупка с промокодом:**

```json
{
  "plan_code": "starter",
  "action": "purchase",
  "period_months": 3,
  "promo_code": "SUMMER20"
}
```

**Запрос — покупка подписки:**

```json
{
  "plan_code": "starter",
  "action": "purchase",
  "period_months": 3
}
```

**Запрос — продление:**

```json
{
  "plan_code": "starter",
  "action": "renew",
  "period_months": 12,
  "subscription_id": "s1s1s1s1-s1s1-s1s1-s1s1-s1s1s1s1s1s1"
}
```

**Запрос — смена тарифа:**

```json
{
  "plan_code": "business",
  "action": "change_plan",
  "period_months": 1,
  "subscription_id": "s1s1s1s1-s1s1-s1s1-s1s1-s1s1s1s1s1s1"
}
```

**Ответ `201`:**

```json
{
  "id": "pay1pay1-pay1-pay1-pay1-pay1pay1pay1pay",
  "plan_id": "11111111-1111-1111-1111-111111111111",
  "user_subscription_id": null,
  "action": "purchase",
  "period_months": 3,
  "provider": "mock",
  "original_amount": 2970,
  "discount_amount": 594,
  "amount": 2376,
  "currency": "RUB",
  "promo_code": "SUMMER20",
  "status": "succeeded",
  "confirmation_url": "http://localhost:8000/cabinet/payments/success",
  "created_at": "2026-06-17T12:00:00+00:00",
  "paid_at": "2026-06-17T12:00:01+00:00",
  "plan": {
    "id": "11111111-1111-1111-1111-111111111111",
    "code": "starter",
    "name": "Стартовый",
    "description": "До 10 сотрудников, 3 филиала, 5 ролей",
    "max_users": 10,
    "max_branches": 3,
    "max_roles": 5,
    "price_monthly": 990
  }
}
```

В режиме `PAYMENT_PROVIDER=mock` оплата подтверждается автоматически.

---

### `GET /api/v1/payments/{payment_id}`

Статус платежа. Требуется JWT.

**Ответ `200`:** объект `PaymentResponse`.

---

### `POST /api/v1/payments/webhook/{provider}`

Webhook от платёжной системы (`mock`, `yookassa`, `cloudpayments`). Тело — JSON провайдера.

**Ответ `200`:**

```json
{
  "status": "succeeded",
  "payment_id": "pay1pay1-pay1-pay1-pay1-pay1pay1pay1pay"
}
```

---

## Глобальная админ-панель — `/api/v1/admin`

Доступ только пользователям с `is_platform_admin: true`. Иначе `403`.

Назначение админов: переменная `PLATFORM_ADMIN_EMAILS` при старте или `PATCH /admin/users/{id}/platform-admin`.

### `GET /api/v1/admin/dashboard`

Сводка по платформе.

**Ответ `200`:**

```json
{
  "users_count": 42,
  "companies_count": 15,
  "successful_payments_count": 28,
  "subscriptions_count": 30,
  "promo_codes_count": 5,
  "active_promo_codes_count": 3,
  "open_support_tickets_count": 7
}
```

---

### `PATCH /api/v1/admin/users/{user_id}/platform-support`

Назначить или снять роль техподдержки платформы. Только `is_platform_admin`.

**Запрос:**

```json
{ "is_platform_support": true }
```

**Ответ `200`:** `AdminUserResponse` с полем `is_platform_support`.

---

### `GET /api/v1/admin/users`

Список пользователей. Query: `limit` (1–200, по умолчанию 50), `offset`.

**Ответ `200`:**

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "ivan@example.com",
    "full_name": "Иван Петров",
    "is_active": true,
    "is_platform_admin": false,
    "is_platform_support": false,
    "created_at": "2026-06-17T12:00:00+00:00"
  }
]
```

---

### `PATCH /api/v1/admin/users/{user_id}/platform-admin`

Назначить или снять права администратора платформы.

**Запрос:**

```json
{ "is_platform_admin": true }
```

**Ответ `200`:** `AdminUserResponse`. Нельзя снять права у самого себя.

---

### `GET /api/v1/admin/companies`

Список всех компаний. Query: `limit`, `offset`.

**Ответ `200`:**

```json
[
  {
    "id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
    "name": "Салон «Лилия»",
    "owner_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "owner_email": "ivan@example.com",
    "owner_name": "Иван Петров",
    "is_owner_first_company": false,
    "created_at": "2026-06-17T12:05:00+00:00"
  }
]
```

---

### `GET /api/v1/admin/promo-codes`

Список промокодов.

**Ответ `200`:**

```json
[
  {
    "id": "pr1pr1pr1-pr1p-r1p1-r1p1-r1p1pr1pr1pr",
    "code": "SUMMER20",
    "discount_percent": 20,
    "user_id": null,
    "user_email": null,
    "user_name": null,
    "plan_codes": ["starter", "business"],
    "actions": ["purchase"],
    "max_uses": 100,
    "used_count": 12,
    "valid_from": null,
    "valid_until": "2026-09-01T00:00:00+00:00",
    "is_active": true,
    "description": "Летняя акция",
    "created_by_id": "admin-uuid",
    "created_at": "2026-06-17T10:00:00+00:00"
  }
]
```

---

### `POST /api/v1/admin/promo-codes`

Создание промокода. Ответ `201`.

**Для всех пользователей:**

```json
{
  "code": "SUMMER20",
  "discount_percent": 20,
  "plan_codes": ["starter"],
  "actions": ["purchase"],
  "max_uses": 100,
  "valid_until": "2026-09-01T00:00:00Z",
  "description": "Летняя акция"
}
```

**Персональный** (`user_email` или `user_id`, по умолчанию `max_uses: 1`):

```json
{
  "code": "IVAN50",
  "discount_percent": 50,
  "user_email": "ivan@example.com",
  "description": "Персональная скидка"
}
```

| Поле | Описание |
|------|----------|
| `plan_codes` | `null` — все тарифы |
| `actions` | `null` — все типы оплаты (`purchase`, `renew`, `change_plan`) |
| `max_uses` | `null` — без лимита |

---

### `PATCH /api/v1/admin/promo-codes/{promo_id}`

Обновление промокода (скидка, лимиты, срок, `is_active`). Код и получатель не меняются.

**Запрос:**

```json
{
  "is_active": false,
  "description": "Акция завершена"
}
```

**Ответ `200`:** `PromoCodeResponse`.

---

## Техподдержка (пользователь) — `/api/v1/support`

Любой авторизованный пользователь может создавать обращения и переписываться с техподдержкой.

### `POST /api/v1/support/tickets`

Создать обращение.

**Запрос:**

```json
{
  "subject": "Не могу оплатить подписку",
  "message": "При checkout получаю ошибку 500"
}
```

**Ответ `201`:** `SupportTicketDetailResponse` (тикет + первое сообщение).

---

### `GET /api/v1/support/tickets`

Список своих обращений.

**Ответ `200`:** массив `SupportTicketResponse`.

---

### `GET /api/v1/support/tickets/{ticket_id}`

Детали обращения с историей сообщений.

**Ответ `200`:** `SupportTicketDetailResponse`.

---

### `POST /api/v1/support/tickets/{ticket_id}/messages`

Добавить сообщение в открытое обращение. Статус тикета → `open`.

**Запрос:**

```json
{ "body": "Прикладываю скриншот ошибки" }
```

**Ответ `201`:** `SupportMessageResponse`. Для закрытых (`resolved`, `closed`) — `400`.

---

## Техподдержка (админка) — `/api/v1/admin/support`

Доступ: `is_platform_support` **или** `is_platform_admin` (`require_platform_staff`). Промокоды и назначение ролей — только у админов.

Назначение support: `PLATFORM_SUPPORT_EMAILS` при старте или `PATCH /admin/users/{id}/platform-support` (от админа).

### Статусы тикета

| status | Описание |
|--------|----------|
| `open` | Новое или ответ пользователя |
| `in_progress` | В работе (назначен исполнитель) |
| `waiting_user` | Ожидается ответ пользователя |
| `resolved` | Решено |
| `closed` | Закрыто |

### `GET /api/v1/admin/support/tickets`

Список всех обращений. Query: `status`, `assigned_to_id`, `limit`, `offset`.

**Ответ `200`:** массив `SupportTicketResponse` (с email/именем пользователя).

---

### `GET /api/v1/admin/support/tickets/{ticket_id}`

Детали обращения.

**Ответ `200`:** `SupportTicketDetailResponse`.

---

### `PATCH /api/v1/admin/support/tickets/{ticket_id}`

Обновить статус и/или назначить исполнителя.

**Запрос:**

```json
{
  "status": "in_progress",
  "assigned_to_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "clear_assignment": false
}
```

`assigned_to_id` — только пользователь с `is_platform_support` или `is_platform_admin`. `clear_assignment: true` снимает назначение.

**Ответ `200`:** `SupportTicketDetailResponse`.

---

### `POST /api/v1/admin/support/tickets/{ticket_id}/messages`

Ответ техподдержки. Статус → `waiting_user`, при первом ответе тикет назначается на текущего сотрудника.

**Запрос:**

```json
{ "body": "Попробуйте обновить страницу и повторить оплату" }
```

**Ответ `201`:** `SupportMessageResponse`.

---

## Услуги и записи — `/api/v1/companies/{company_id}`

Право `manage_services` или владелец — создание/изменение услуг и записей. Просмотр — любой участник компании.

### `POST /api/v1/companies/{company_id}/services`

Создать услугу с длительностью.

**Запрос:**

```json
{
  "name": "Стрижка",
  "description": "Мужская стрижка",
  "duration_minutes": 60,
  "price": 1500,
  "member_id": null,
  "branch_id": null
}
```

| Поле | Описание |
|------|----------|
| `duration_minutes` | 5–480 минут; определяет, сколько слотов занимает запись |
| `member_id` | Опционально — услуга только у этого специалиста |
| `branch_id` | Опционально — привязка к филиалу |

**Ответ `201`:** `CompanyServiceResponse`.

---

### `GET /api/v1/companies/{company_id}/services`

Список услуг. Query: `active_only`, `member_id` (услуги компании + услуги без привязки к специалисту).

---

### `PATCH /api/v1/companies/{company_id}/services/{service_id}`

Обновление услуги. Флаги `clear_member`, `clear_branch` снимают привязки.

---

### `POST /api/v1/companies/{company_id}/members/{member_id}/appointments`

Записать клиента на услугу. Время должно быть доступным слотом с учётом длительности услуги и существующих записей.

**Запрос:**

```json
{
  "service_id": "s1s1s1s1-s1s1-s1s1-s1s1-s1s1s1s1s1s1",
  "starts_at": "2026-06-20T10:00:00+00:00",
  "client_name": "Анна",
  "client_phone": "+79001234567",
  "note": "Первый визит"
}
```

**Ответ `201`:** `AppointmentResponse` с полем `ends_at`.

При пересечении с другой записью — `409`.

---

### `GET /api/v1/companies/{company_id}/members/{member_id}/appointments`

Список записей. Query: `from_date`, `to_date`, `status`.

---

### `PATCH /api/v1/companies/{company_id}/members/{member_id}/appointments/{appointment_id}`

Изменить статус (`scheduled`, `cancelled`, `completed`) или данные клиента.

---

### `DELETE /api/v1/companies/{company_id}/members/{member_id}/appointments/{appointment_id}`

Отменить запись (статус → `cancelled`).

---

## Компании — `/api/v1/companies`

### `POST /api/v1/companies`

Создание компании. Требуется JWT и **свободная подписка** (`subscription_id` без привязанной компании).

**Запрос:**

```json
{
  "name": "Салон красоты «Лилия»",
  "subscription_id": "s1s1s1s1-s1s1-s1s1-s1s1-s1s1s1s1s1s1"
}
```

**Ответ `201`:**

```json
{
  "id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
  "name": "Салон красоты «Лилия»",
  "owner_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "is_owner_first_company": false,
  "created_at": "2026-06-17T12:05:00+00:00",
  "has_active_subscription": true,
  "is_owner": true
}
```

---

### `GET /api/v1/companies`

Список компаний пользователя (владелец или участник). Требуется JWT.

**Ответ `200`:** массив `CompanyResponse`.

---

### `GET /api/v1/companies/{company_id}`

Одна компания. Доступ: владелец или участник. Требуется JWT.

**Ответ `200`:** `CompanyResponse`.

**Ошибка `404`:** нет доступа или компания не существует.

---

### `GET /api/v1/companies/{company_id}/limits`

Лимиты подписки и текущее использование. Требуется JWT.

**Ответ `200`:**

```json
{
  "max_users": 10,
  "max_branches": 3,
  "max_roles": 5,
  "current_users": 2,
  "current_branches": 1,
  "current_roles": 2,
  "has_active_subscription": true,
  "expires_at": "2026-09-17T12:00:00+00:00",
  "scheduled_plan_code": null,
  "scheduled_change_at": null
}
```

---

## Роли — `/api/v1/companies/{company_id}/roles`

### `POST /api/v1/companies/{company_id}/roles`

Создание роли. Право: `manage_roles` или владелец. Требуется JWT и активная подписка.

**Запрос:**

```json
{
  "name": "Менеджер персонала",
  "description": "Управление сотрудниками и расписанием",
  "permissions": ["manage_members", "manage_schedules", "manage_join_requests"]
}
```

**Ответ `201`:**

```json
{
  "id": "r1r1r1r1-r1r1-r1r1-r1r1-r1r1r1r1r1r1",
  "company_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
  "name": "Менеджер персонала",
  "description": "Управление сотрудниками и расписанием",
  "permissions": ["manage_members", "manage_schedules", "manage_join_requests"],
  "created_at": "2026-06-17T12:20:00+00:00"
}
```

---

### `PATCH /api/v1/companies/{company_id}/roles/{role_id}`

Обновление роли (имя, описание, права). Право: `manage_roles`.

**Запрос:**

```json
{
  "permissions": ["manage_members", "manage_schedules"]
}
```

**Ответ `200`:** `CompanyRoleResponse`.

---

### `GET /api/v1/companies/{company_id}/roles`

Список ролей. Требуется JWT.

**Ответ `200`:** массив `CompanyRoleResponse`.

---

## Сотрудники — `/api/v1/companies/{company_id}/members`

### `GET /api/v1/companies/{company_id}/members`

Список участников. Требуется JWT.

**Ответ `200`:**

```json
[
  {
    "id": "m1m1m1m1-m1m1-m1m1-m1m1-m1m1m1m1m1m1",
    "company_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
    "user_id": "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2",
    "role_id": "r2r2r2r2-r2r2-r2r2-r2r2-r2r2r2r2r2r2",
    "created_at": "2026-06-17T12:25:00+00:00"
  }
]
```

---

### `PATCH /api/v1/companies/{company_id}/members/{member_id}`

Смена роли сотрудника. Право: `manage_members` или владелец.

**Запрос:**

```json
{
  "role_id": "r2r2r2r2-r2r2-r2r2-r2r2-r2r2r2r2r2r2"
}
```

**Ответ `200`:** `CompanyMemberResponse`.

---

## Приглашения — `/api/v1/companies/{company_id}/join-requests`

### `POST /api/v1/companies/{company_id}/join-requests`

Пригласить пользователя по email. Право: `manage_join_requests` или владелец. Требуется активная подписка.

**Запрос:**

```json
{
  "email": "master@example.com",
  "role_id": "r2r2r2r2-r2r2-r2r2-r2r2-r2r2r2r2r2r2",
  "message": "Приглашаем в команду"
}
```

**Ответ `201`:**

```json
{
  "id": "j1j1j1j1-j1j1-j1j1-j1j1-j1j1j1j1j1j1",
  "company_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
  "user_id": "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2",
  "role_id": "r2r2r2r2-r2r2-r2r2-r2r2-r2r2r2r2r2r2",
  "invited_by_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "Приглашаем в команду",
  "created_at": "2026-06-17T12:30:00+00:00",
  "responded_at": null,
  "role_name": "Мастер"
}
```

---

### `GET /api/v1/companies/{company_id}/join-requests`

Список отправленных приглашений. Право: `manage_join_requests`.

**Ответ `200`:** массив `JoinRequestResponse`.

---

## Филиалы — `/api/v1/companies/{company_id}/branches`

### `POST /api/v1/companies/{company_id}/branches`

Создание филиала. Право: `manage_branches`. Требуется активная подписка.

**Запрос:**

```json
{
  "name": "Филиал на Ленина",
  "address": "г. Москва, ул. Ленина, д. 10"
}
```

**Ответ `201`:**

```json
{
  "id": "f1f1f1f1-f1f1-f1f1-f1f1-f1f1f1f1f1f1",
  "company_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
  "name": "Филиал на Ленина",
  "address": "г. Москва, ул. Ленина, д. 10",
  "created_at": "2026-06-17T12:35:00+00:00"
}
```

---

### `GET /api/v1/companies/{company_id}/branches`

Список филиалов. Требуется JWT.

**Ответ `200`:** массив `BranchResponse`.

---

## Расписание записей — `/api/v1/companies/{company_id}/members/{member_id}/schedules`

Право: `manage_schedules` или владелец. Требуется активная подписка компании.

### `POST .../schedules`

Создание расписания для специалиста (сотрудника).

**Параметры:**

| Поле | Описание |
|------|----------|
| `date_from`, `date_to` | Период действия (макс. 365 дней) |
| `time_start`, `time_end` | Окно записи в течение дня |
| `slot_interval_minutes` | Интервал между слотами (5–480 мин) |
| `pattern_type` | `weekly`, `cycle` или `manual` |
| `pattern_config` | Настройки рабочих дней (см. ниже) |

**Пример — пн–пт, интервал 1 час:**

```json
{
  "date_from": "2026-06-17",
  "date_to": "2026-12-17",
  "time_start": "08:00:00",
  "time_end": "17:00:00",
  "slot_interval_minutes": 60,
  "pattern_type": "weekly",
  "pattern_config": {
    "weekday_off": [5, 6],
    "extra_off_dates": ["2026-01-01"],
    "extra_work_dates": []
  }
}
```

Слоты: `08:00`, `09:00`, … `16:00`.

**Пример — цикл 2/2:**

```json
{
  "date_from": "2026-06-17",
  "date_to": "2026-12-17",
  "time_start": "09:00:00",
  "time_end": "18:00:00",
  "slot_interval_minutes": 30,
  "pattern_type": "cycle",
  "pattern_config": {
    "work_days": 2,
    "rest_days": 2,
    "anchor_date": "2026-06-17"
  }
}
```

**Пример — произвольные дни:**

```json
{
  "date_from": "2026-06-17",
  "date_to": "2026-06-30",
  "time_start": "10:00:00",
  "time_end": "14:00:00",
  "slot_interval_minutes": 60,
  "pattern_type": "manual",
  "pattern_config": {
    "days": {
      "2026-06-17": true,
      "2026-06-18": true,
      "2026-06-19": false
    }
  }
}
```

**Ответ `201`:**

```json
{
  "id": "sch1sch1-sch1-sch1-sch1-sch1sch1sch1",
  "company_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
  "member_id": "m1m1m1m1-m1m1-m1m1-m1m1-m1m1m1m1m1m1",
  "date_from": "2026-06-17",
  "date_to": "2026-12-17",
  "time_start": "08:00:00",
  "time_end": "17:00:00",
  "slot_interval_minutes": 60,
  "pattern_type": "weekly",
  "pattern_config": {
    "weekday_off": [5, 6],
    "extra_off_dates": [],
    "extra_work_dates": []
  },
  "created_by_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_at": "2026-06-17T12:40:00+00:00"
}
```

---

### `GET .../schedules`

Список расписаний специалиста. Требуется JWT.

**Ответ `200`:** массив `WorkScheduleResponse`.

---

### `GET .../schedules/{schedule_id}/slots`

Расчёт слотов за период.

**Query-параметры:**

| Параметр | Описание |
|----------|----------|
| `from_date` | Начало периода (YYYY-MM-DD) |
| `to_date` | Конец периода (YYYY-MM-DD) |
| `service_id` | Опционально — услуга; слоты фильтруются по её `duration_minutes` |

**Ответ `200`:**

```json
{
  "schedule_id": "sch1sch1-sch1-sch1-sch1-sch1sch1sch1",
  "member_id": "m1m1m1m1-m1m1-m1m1-m1m1-m1m1m1m1m1m1",
  "from_date": "2026-06-17",
  "to_date": "2026-06-19",
  "service_id": "s1s1s1s1-s1s1-s1s1-s1s1-s1s1s1s1s1s1",
  "booking_duration_minutes": 60,
  "slots_by_day": {
    "2026-06-17": ["08:00", "09:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
  }
}
```

Слоты учитывают **исключения расписания** и **существующие записи** (`appointments`). Если услуга на 60 минут заняла 10:00–11:00, слоты 10:00 и 10:30 (при интервале 30 мин) не отображаются. С `service_id` дополнительно скрываются слоты, куда услуга не помещается по длительности или из‑за пересечения с записями.

---

## Исключения расписания — `.../schedule-exceptions`

Право: `manage_schedules` или владелец. Создание/удаление требует активную подписку.

### Даты исключения

Указывается **один** из способов (максимальный размах — **365 дней**):

| Способ | Поля | Пример |
|--------|------|--------|
| Один день | `exception_date` | `"2026-06-20"` |
| Диапазон дат | `date_from`, `date_to` | `"2026-06-17"` … `"2026-06-24"` |
| Несколько дней | `dates` | `["2026-06-17", "2026-06-19", "2026-06-22"]` |

Одинаковые `block_config` применяются ко **всем** указанным дням.

### `POST /api/v1/companies/{company_id}/members/{member_id}/schedule-exceptions`

**Выходной на один день:**

```json
{
  "exception_date": "2026-06-20",
  "kind": "day_off",
  "note": "Отпуск"
}
```

**Выходной на диапазон:**

```json
{
  "date_from": "2026-07-01",
  "date_to": "2026-07-14",
  "kind": "day_off",
  "note": "Отпуск"
}
```

**Блокировка слотов на несколько дней (диапазон времени каждый день):**

```json
{
  "date_from": "2026-06-17",
  "date_to": "2026-06-21",
  "kind": "slot_block",
  "block_config": {
    "mode": "range",
    "time_from": "10:00",
    "time_to": "13:00"
  }
}
```

**Блокировка на выбранные даты (конкретные времена):**

```json
{
  "dates": ["2026-06-17", "2026-06-19", "2026-06-22"],
  "kind": "slot_block",
  "block_config": {
    "mode": "times",
    "times": ["09:00", "15:30"]
  }
}
```

**Блокировка одного дня диапазоном времени:**

```json
{
  "exception_date": "2026-06-18",
  "kind": "slot_block",
  "block_config": {
    "mode": "range",
    "time_from": "10:00",
    "time_to": "13:00"
  }
}
```

**Ответ `201`:**

```json
{
  "id": "ex1ex1ex1-ex1e-x1e1-ex1e-ex1ex1ex1ex1",
  "company_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
  "member_id": "m1m1m1m1-m1m1-m1m1-m1m1-m1m1m1m1m1m1",
  "exception_date": "2026-07-01",
  "exception_date_to": "2026-07-14",
  "exception_dates": null,
  "kind": "day_off",
  "block_config": null,
  "note": "Отпуск",
  "created_by_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_at": "2026-06-17T14:00:00+00:00"
}
```

Для списка `dates` в ответе: `exception_dates` — массив ISO-дат, `exception_date` / `exception_date_to` — минимум и максимум.

Пересечение `day_off` с уже назначенными выходными → `409`. Несколько `slot_block` на одни и те же дни допустимо.

---

### `GET .../schedule-exceptions`

Список исключений. Query: `from_date`, `to_date` (опционально). Просмотр — любой участник компании.

**Ответ `200`:** массив `ScheduleExceptionResponse`.

---

### `DELETE .../schedule-exceptions/{exception_id}`

Удаление исключения. Ответ `204`.

---

## Типичные сценарии

### Владелец — от нуля до расписания

```
1. POST /auth/register
2. POST /auth/login
3. POST /payments/checkout/preview     { action: "purchase", plan_code, period_months, promo_code? }
4. POST /payments/checkout             { ... }
5. GET  /cabinet                       → subscription_id
6. POST /companies                     { name, subscription_id }
7. POST /companies/{id}/roles
8. POST /companies/{id}/join-requests
9. POST /companies/{id}/members/{id}/schedules
10. POST /companies/{id}/members/{id}/schedule-exceptions  (выходной / блок слотов)
```

### Сотрудник

```
1. POST /auth/register
2. GET  /cabinet/join-requests
3. POST /cabinet/join-requests/{id}/accept
```

### Администратор платформы

```
1. POST /auth/login                    (пользователь из PLATFORM_ADMIN_EMAILS)
2. GET  /admin/dashboard
3. POST /admin/promo-codes             { code, discount_percent, ... }
4. PATCH /admin/users/{id}/platform-admin
```

---

## Коды ошибок

```json
{ "detail": "Текст ошибки" }
```

| Код | Когда |
|-----|-------|
| `400` | Некорректные данные, невалидный промокод при checkout |
| `401` | Не авторизован |
| `403` | Нет подписки / превышен лимит / нет прав platform admin |
| `404` | Не найдено или нет доступа к компании |
| `409` | Конфликт (дубликат, выходной уже назначен) |
| `422` | Ошибка валидации полей |

**Пример `422`:**

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "input": "123"
    }
  ]
}
```
