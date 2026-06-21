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
| Клиенты | `/api/v1/companies/{id}/clients` | JWT + tenant |
| Склад | `/api/v1/companies/{id}/warehouse` | JWT + tenant |
| Отзывы | `/api/v1/companies/{id}/reviews`, `/public/booking/{slug}/reviews` | JWT / — |

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
  { "code": "manage_company", "label": "Редактирование профиля компании" },
  { "code": "manage_warehouse", "label": "Управление складом и движением товаров" },
  { "code": "manage_join_requests", "label": "Приглашения в компанию" },
  { "code": "manage_members", "label": "Управление сотрудниками (смена ролей)" },
  { "code": "manage_roles", "label": "Управление ролями и правами" },
  { "code": "manage_schedules", "label": "Настройка расписания записей" },
  { "code": "manage_services", "label": "Управление услугами и записями клиентов" },
  { "code": "view_statistics", "label": "Просмотр статистики и дашборда" }
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

Список тарифов с учётом **активных акций** (скидка применяется автоматически, без промокода). Авторизация не требуется.

При активной акции в ответе есть `price_monthly` (без скидки), `promotional_price_monthly` (со скидкой) и `active_promotion`.

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
    "max_services": 10,
    "max_appointments_per_month": 100,
    "price_monthly": 990,
    "promotional_price_monthly": 792,
    "active_promotion": {
      "id": "promo-uuid",
      "name": "Старт со скидкой 20%",
      "discount_percent": 20,
      "first_plan_purchase_only": false
    }
  }
]
```

Если акции нет — `promotional_price_monthly` и `active_promotion` равны `null`.

---

### `GET /api/v1/companies/{company_id}/subscription/available-plans`

Тарифы, доступные для смены с учётом текущего использования и **активных акций** для этой компании (включая проверку «первая покупка тарифа»). Только владелец. Требуется JWT.

**Ответ `200`:** массив `SubscriptionPlanResponse` (см. поля `promotional_price_monthly`, `active_promotion`).

---

### `POST /api/v1/payments/checkout/preview`

Предпросмотр оплаты **до нажатия «Оплатить»**: расчёт суммы, автоматическое применение акции и опциональная проверка промокода. Требуется JWT.

Акция применяется автоматически. Если указан промокод с большей скидкой — используется промокод (не суммируются).

**Запрос** (те же поля, что у checkout):

```json
{
  "plan_code": "starter",
  "action": "purchase",
  "period_months": 3,
  "promo_code": "SUMMER20"
}
```

**Ответ `200` — акция применена автоматически:**

```json
{
  "plan": {
    "code": "starter",
    "name": "Стартовый",
    "price_monthly": 990,
    "promotional_price_monthly": 792,
    "active_promotion": {
      "id": "promo-uuid",
      "name": "Старт со скидкой 20%",
      "discount_percent": 20,
      "first_plan_purchase_only": true
    }
  },
  "action": "purchase",
  "period_months": 3,
  "original_amount": 2970,
  "discount_amount": 594,
  "amount": 2376,
  "currency": "RUB",
  "promo_code": null,
  "promo_applied": false,
  "promo_error": null,
  "promotion_id": "promo-uuid",
  "promotion_name": "Старт со скидкой 20%",
  "promotion_applied": true
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
  "subscription_promotions_count": 2,
  "active_subscription_promotions_count": 1,
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

Список всех компаний с подписками и статусом оплаты. Query: `limit`, `offset`.

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
    "created_at": "2026-06-17T12:05:00+00:00",
    "subscription_id": "s1s1s1s1-s1s1-s1s1-s1s1-s1s1s1s1s1s1",
    "plan_code": "starter",
    "plan_name": "Стартовый",
    "subscription_status": "active",
    "expires_at": "2026-07-17T12:00:00+00:00",
    "is_subscription_active": true,
    "is_paid": true,
    "is_free_plan": false,
    "last_payment_status": "succeeded",
    "last_payment_paid_at": "2026-06-17T12:00:00+00:00",
    "last_payment_amount": 990
  }
]
```

| Поле | Описание |
|------|----------|
| `is_subscription_active` | Подписка активна и не истекла |
| `is_paid` | Последний платёж по подписке успешен |
| `is_free_plan` | Тариф `basic` (бесплатный), `is_paid` = false |

---

### `GET /api/v1/admin/announcements`

Список объявлений платформы (техработы и т.п.).

---

### `POST /api/v1/admin/announcements`

Создать объявление для **всех компаний**. Сразу видно пользователям в кабинете и `GET /announcements`.

**Запрос:**

```json
{
  "title": "Плановые технические работы",
  "message": "17 июня с 02:00 до 04:00 MSK возможны перерывы в работе сервиса",
  "maintenance_starts_at": "2026-06-17T23:00:00+00:00",
  "maintenance_ends_at": "2026-06-18T01:00:00+00:00"
}
```

**Ответ `201`:** `PlatformAnnouncementResponse`.

---

### `PATCH /api/v1/admin/announcements/{announcement_id}`

Обновить или снять с публикации (`is_active: false`).

---

### `GET /api/v1/announcements`

Активные объявления для авторизованных пользователей (все компании).

**Ответ `200`:** массив с полями `title`, `message`, `maintenance_starts_at`, `maintenance_ends_at`.

Также включены в `GET /api/v1/cabinet` → `platform_announcements`.

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

## Акции на подписки — `/api/v1/admin/subscription-promotions`

**Акции** в отличие от промокодов применяются **автоматически**: пользователь видит `price_monthly` и `promotional_price_monthly` в списке тарифов и при checkout без ввода кода.

Доступ: platform admin.

### `GET /api/v1/admin/subscription-promotions`

Список акций.

**Ответ `200`:**

```json
[
  {
    "id": "promo-uuid",
    "name": "Старт со скидкой 20%",
    "discount_percent": 20,
    "plan_codes": ["starter"],
    "actions": ["purchase"],
    "for_all_companies": true,
    "company_ids": null,
    "first_plan_purchase_only": true,
    "max_uses": null,
    "used_count": 5,
    "valid_from": null,
    "valid_until": "2026-09-01T00:00:00+00:00",
    "is_active": true,
    "description": "Скидка на первую покупку тарифа",
    "created_by_id": "admin-uuid",
    "created_at": "2026-06-17T10:00:00+00:00"
  }
]
```

### `POST /api/v1/admin/subscription-promotions`

Создание акции. Ответ `201`.

**Для всех организаций, только первая покупка тарифа:**

```json
{
  "name": "Старт со скидкой 20%",
  "discount_percent": 20,
  "plan_codes": ["starter"],
  "actions": ["purchase"],
  "for_all_companies": true,
  "first_plan_purchase_only": true,
  "valid_until": "2026-09-01T00:00:00Z",
  "description": "Скидка при первой покупке тарифа у компании"
}
```

**Для выбранных компаний** (`for_all_companies: false`, обязателен `company_ids`):

```json
{
  "name": "Партнёрская скидка",
  "discount_percent": 15,
  "for_all_companies": false,
  "company_ids": ["company-uuid-1", "company-uuid-2"]
}
```

| Поле | Описание |
|------|----------|
| `for_all_companies` | `true` — акция для всех организаций |
| `first_plan_purchase_only` | `true` — только если компания ещё не оплачивала этот тариф |
| `plan_codes` | `null` — все тарифы |
| `actions` | `null` — все типы оплаты |
| `company_ids` | UUID компаний, если `for_all_companies: false` |

### `PATCH /api/v1/admin/subscription-promotions/{promotion_id}`

Обновление акции (скидка, срок, `is_active`, список компаний). Ответ `200`: `SubscriptionPromotionResponse`.

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
  "category": "Парикмахерские",
  "description": "Мужская стрижка",
  "duration_minutes": 60,
  "buffer_before_minutes": 5,
  "buffer_after_minutes": 15,
  "price": 1500,
  "member_id": "m1m1m1m1-m1m1-m1m1-m1m1-m1m1m1m1m1m1",
  "branch_id": null
}
```

| Поле | Описание |
|------|----------|
| `category` | Категория услуги (опционально) |
| `description` | Описание услуги (опционально) |
| `duration_minutes` | 5–480 минут; длительность самой услуги |
| `buffer_before_minutes` | Буфер до услуги: `0`, `5`, `10`, `15`, `30` |
| `buffer_after_minutes` | Буфер после услуги: `0`, `5`, `10`, `15`, `30` |
| `price` | Цена в копейках/рублях (опционально) |
| `member_id` | Исполнитель — сотрудник компании (опционально) |
| `branch_id` | Опционально — привязка к филиалу |

**Ответ `201`:** `CompanyServiceResponse` с полями `category`, `buffer_before_minutes`, `buffer_after_minutes`, `member_name`.

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
  "client_full_name": "Иванова Анна Петровна",
  "client_phone": "+79001234567",
  "client_email": "anna@example.com",
  "note": "Первый визит"
}
```

| Поле | Описание |
|------|----------|
| `client_name` | Имя (обязательно `client_name` или `client_full_name`) |
| `client_full_name` | ФИО |
| `client_phone` | Телефон (обязателен); по нему клиенты объединяются в рамках компании |
| `client_email` | Email (опционально) |
| `note` | Дополнительная информация, до 2000 символов |

При создании записи создаётся или обновляется карточка клиента (`CompanyClient`) в компании. Один номер телефона — один человек.

**Ответ `201`:** `AppointmentResponse` с полями `client_id`, `ends_at`, `member_name`.

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

### Клиенты и история записей

Клиент в компании определяется по **нормализованному номеру телефона** (8→7, 10 цифр → +7). Все записи с одним телефоном попадают в одну историю.

Просмотр — любой участник компании.

#### `GET /api/v1/companies/{company_id}/clients/lookup?phone=`

Найти карточку клиента по телефону.

**Ответ `200`:** `CompanyClientResponse` (`id`, `phone`, `name`, `full_name`, `email`, `appointments_count`).

**404** — клиент с таким телефоном ещё не записывался.

#### `GET /api/v1/companies/{company_id}/clients/history?phone=`

История записей клиента по телефону.

**Ответ `200`:** `ClientHistoryResponse`:

```json
{
  "client": { "id": "...", "phone": "+7 (900) 123-45-67", "name": "Анна", "appointments_count": 2 },
  "appointments": [
    {
      "id": "...",
      "service_name": "Стрижка",
      "member_name": "Мария",
      "branch_name": "Центр",
      "starts_at": "2026-06-20T10:00:00+00:00",
      "ends_at": "2026-06-20T11:00:00+00:00",
      "status": "completed",
      "note": "Первый визит"
    }
  ]
}
```

Каждый элемент истории содержит: куда (`branch_name`), как (`service_name`), к кому (`member_name`), когда (`starts_at`, `ends_at`), снимок контактов и заметку на момент записи.

#### `GET /api/v1/companies/{company_id}/clients/{client_id}/history`

Та же история по `client_id` из ответа записи или lookup.

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

Одна компания с полным профилем и галереей. Доступ: владелец или участник. Требуется JWT.

**Ответ `200`:** `CompanyResponse` с полями профиля, `logo_url`, `gallery`.

**Ошибка `404`:** нет доступа или компания не существует.

---

### `PATCH /api/v1/companies/{company_id}`

Редактирование профиля компании. Право: `manage_company`, `manage_members` или владелец.

**Запрос:**

```json
{
  "name": "Салон «Лилия»",
  "country": "Россия",
  "city": "Москва",
  "address": "ул. Примерная, 1",
  "phone": "+74951234567",
  "organization_type": "ip",
  "working_hours": {
    "monday": { "open": "09:00", "close": "21:00" },
    "tuesday": { "open": "09:00", "close": "21:00" },
    "sunday": { "is_closed": true }
  }
}
```

| Поле | Описание |
|------|----------|
| `name` | Название (обязательное при передаче) |
| `country`, `city`, `address` | Локация |
| `phone` | Телефон компании (отдельно от телефона владельца) |
| `organization_type` | `ip` (ИП), `self_employed` (самозанятый), `llc` (ООО) |
| `working_hours` | График работы по дням недели |
| `clear_*` | Флаги сброса опциональных полей |
| `booking_slug` | Часть ссылки онлайн-записи (латиница, цифры, дефис) |
| `public_booking_enabled` | Включить публичную запись; при включении без slug он генерируется из названия |

**Ответ `200`:** обновлённый `CompanyResponse` с полями `booking_slug`, `public_booking_enabled`, `booking_url`.

---

### Логотип и фото студии

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/companies/{id}/logo` или `/photo` | Загрузить логотип (JPEG, PNG, WebP) |
| `DELETE` | `/companies/{id}/logo` или `/photo` | Удалить логотип |
| `POST` | `/companies/{id}/gallery` | Добавить фото студии (до 20 шт.) |
| `DELETE` | `/companies/{id}/gallery/{photo_id}` | Удалить фото из галереи |

---

### Реквизиты организации

Отдельная сущность для выставления счетов. Одна запись на компанию.

#### `GET /api/v1/companies/{company_id}/requisites`

Просмотр реквизитов. Доступ: участник компании.

**Ответ `200`:** `CompanyRequisitesResponse`.

**404** — реквизиты ещё не заполнены.

#### `PUT /api/v1/companies/{company_id}/requisites`

Создание или обновление реквизитов. Право: `manage_company`, `manage_members` или владелец.

**Запрос:**

```json
{
  "name": "ООО «Лилия»",
  "inn": "7701234567",
  "kpp": "770101001",
  "billing_email": "buh@lilia.example.com"
}
```

| Поле | Описание |
|------|----------|
| `name` | Название организации для документов |
| `inn` | ИНН: 10 цифр (юрлицо) или 12 (ИП/физлицо) |
| `kpp` | КПП: 9 цифр (опционально, для ИП обычно не указывается) |
| `billing_email` | Email для отправки счетов |

**Ответ `200`:** `CompanyRequisitesResponse`.

---

## Онлайн-запись для клиентов — `/api/v1/public/booking`

Публичные эндпоинты **без JWT**. Компания должна иметь `public_booking_enabled: true`, уникальный `booking_slug` и активную подписку.

Ссылка для клиентов: `{PUBLIC_BOOKING_BASE_URL}/{slug}` (по умолчанию `http://localhost:8000/book/{slug}`). Поле `booking_url` возвращается в `CompanyResponse` после включения записи.

### Сценарий записи

1. `GET /public/booking/{slug}` — страница компании
2. `GET /public/booking/{slug}/members` — выбор мастера
3. `GET /public/booking/{slug}/services?member_id=` — услуги мастера
4. `GET /public/booking/{slug}/members/{member_id}/slots?service_id=&from_date=&to_date=` — свободные слоты
5. `POST /public/booking/{slug}/members/{member_id}/appointments` — создание записи

Медиа (логотип, фото) для публичной страницы: `GET /api/v1/public/media/{path}` — только если у компании включена онлайн-запись.

### `GET /api/v1/public/booking/{slug}`

**Ответ `200`:** название, адрес, телефон, график работы, логотип, галерея.

### `GET /api/v1/public/booking/{slug}/members`

**Ответ `200`:** массив `{ id, full_name, role_name, photo_url }` — специалисты с расписанием или услугами.

### `GET /api/v1/public/booking/{slug}/services`

Query: `member_id` (опционально). Только активные услуги.

### `GET /api/v1/public/booking/{slug}/members/{member_id}/slots`

Query: `service_id`, `from_date`, `to_date` (до 60 дней). **Ответ:** `slots_by_day` — время начала услуги.

### `POST /api/v1/public/booking/{slug}/members/{member_id}/appointments`

**Запрос** (как `AppointmentCreate`):

```json
{
  "service_id": "...",
  "starts_at": "2026-06-20T10:00:00+00:00",
  "client_name": "Анна",
  "client_phone": "+79001234567",
  "client_email": "anna@example.com",
  "note": "Комментарий"
}
```

**Ответ `201`:** подтверждение записи (`id`, `starts_at`, `ends_at`, `service_name`, `member_name`).

### Отзывы клиентов

Отзыв о **компании** (оценка 1–5 и текст). Можно указать **мастера**, к которому ходил клиент. Оставить отзыв может только клиент с записью в компании (по номеру телефона).

#### `GET /api/v1/public/booking/{slug}/reviews`

Публичный список отзывов и **рейтинг компании** (`rating.average`, `rating.count`).

#### `GET /api/v1/public/booking/{slug}/reviews/visit-members?phone=`

Мастера, к которым клиент записывался (для выбора в форме отзыва).

#### `POST /api/v1/public/booking/{slug}/reviews`

**Запрос:**

```json
{
  "client_phone": "+79001234567",
  "client_name": "Анна",
  "member_id": "...",
  "rating": 5,
  "text": "Отличный сервис, вернусь снова!"
}
```

| Поле | Описание |
|------|----------|
| `rating` | Оценка компании от 1 до 5 |
| `member_id` | Опционально — мастер из списка visit-members |
| `text` | Текст отзыва, от 10 символов |

На странице компании (`GET /public/booking/{slug}`) также возвращаются `rating_average` и `rating_count`.

#### `GET /api/v1/companies/{company_id}/reviews`

Все отзывы для сотрудников компании (включая скрытые поля). JWT + участник компании.

---

## Дашборд и статистика — `/api/v1/companies/{company_id}/dashboard`

Агрегированная статистика по записям и выручке. Доступ: **владелец компании** или участник с правом `view_statistics`. Без доступа — ответ `404`.

Учёт ведётся по полю `starts_at` записи (время начала приёма).

### `GET /api/v1/companies/{company_id}/dashboard`

Query-параметры периода (указывается **один** вариант):

| Параметр | Описание |
|----------|----------|
| `date` | Статистика за один день (`YYYY-MM-DD`) |
| `month` | Календарный месяц (`YYYY-MM`) |
| `from_date`, `to_date` | Произвольный диапазон (не более 366 дней) |
| *(без параметров)* | Текущий календарный месяц (с 1-го числа по последний день месяца) |

**Ответ `200`:**

```json
{
  "period_from": "2026-06-01",
  "period_to": "2026-06-30",
  "appointments_count": 42,
  "scheduled_count": 8,
  "completed_services_count": 30,
  "cancelled_count": 4,
  "revenue": 87500,
  "by_day": [
    {
      "date": "2026-06-01",
      "appointments_count": 3,
      "completed_services_count": 2,
      "revenue": 5500
    }
  ]
}
```

| Поле | Описание |
|------|----------|
| `appointments_count` | Записи, кроме отменённых |
| `scheduled_count` | Запланированные |
| `completed_services_count` | Выполненные услуги |
| `cancelled_count` | Отменённые |
| `revenue` | Сумма цен услуг по выполненным записям (текущая цена услуги в каталоге) |
| `by_day` | Разбивка по дням; заполняется, если период больше одного дня |

Чтобы выдать менеджеру доступ к статистике, добавьте право `view_statistics` в его роль (`PATCH /companies/{id}/roles/{role_id}`).

---

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

## Склад — `/api/v1/companies/{company_id}/warehouse`

Учёт **товаров** (`product`) и **расходников** (`consumable`), остатки по основному складу и филиалам, история движений.

Право `manage_warehouse` или владелец — создание позиций и движений. Просмотр — любой участник компании.

### `POST /api/v1/companies/{company_id}/warehouse/items`

Создать позицию склада.

```json
{
  "name": "Шампунь профессиональный",
  "item_type": "consumable",
  "sku": "SHMP-001",
  "unit": "мл",
  "description": "500 мл",
  "min_quantity": 1000,
  "initial_quantity": 5000,
  "branch_id": null
}
```

| Поле | Описание |
|------|----------|
| `item_type` | `product` (товар) или `consumable` (расходник) |
| `initial_quantity` | Опционально — создаёт приход «Начальный остаток» |
| `branch_id` | Филиал для начального остатка (`null` — основной склад) |

### `GET /api/v1/companies/{company_id}/warehouse/items`

Список позиций. Query: `item_type`, `active_only`.

**Ответ:** `WarehouseItemResponse` с остатками по локациям и флагом `is_low_stock`.

### `PATCH /api/v1/companies/{company_id}/warehouse/items/{item_id}`

Обновление карточки (не меняет остаток напрямую).

### `GET /api/v1/companies/{company_id}/warehouse/stock`

Таблица остатков. Query: `item_type`, `branch_id`.

### `POST /api/v1/companies/{company_id}/warehouse/movements`

Движение по складу.

**Приход:**

```json
{
  "item_id": "...",
  "movement_type": "receipt",
  "quantity": 100,
  "branch_id": null,
  "note": "Поставка от поставщика"
}
```

**Расход:**

```json
{
  "item_id": "...",
  "movement_type": "issue",
  "quantity": 5,
  "branch_id": null,
  "note": "Списание на услугу"
}
```

**Корректировка (инвентаризация):**

```json
{
  "item_id": "...",
  "movement_type": "adjustment",
  "quantity_delta": -2,
  "branch_id": null,
  "note": "Недостача при пересчёте"
}
```

**Перемещение между складами/филиалами:**

```json
{
  "item_id": "...",
  "movement_type": "transfer",
  "quantity": 20,
  "from_branch_id": null,
  "to_branch_id": "...",
  "note": "Пополнение филиала"
}
```

| Тип | Описание |
|-----|----------|
| `receipt` | Приход |
| `issue` | Расход |
| `adjustment` | Корректировка (`quantity_delta` ±) |
| `transfer` | Перемещение между `from_branch_id` и `to_branch_id` |

При недостатке остатка — `400`.

### `GET /api/v1/companies/{company_id}/warehouse/movements`

История движений. Query: `item_id`, `movement_type`, `from_date`, `to_date`, `limit`.

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
| `service_id` | Опционально — услуга; слоты фильтруются по длительности и буферам услуги |

**Ответ `200`:**

```json
{
  "schedule_id": "sch1sch1-sch1-sch1-sch1-sch1sch1sch1",
  "member_id": "m1m1m1m1-m1m1-m1m1-m1m1-m1m1m1m1m1m1",
  "from_date": "2026-06-17",
  "to_date": "2026-06-19",
  "service_id": "s1s1s1s1-s1s1-s1s1-s1s1-s1s1s1s1s1s1",
  "booking_duration_minutes": 60,
  "buffer_before_minutes": 5,
  "buffer_after_minutes": 15,
  "slots_by_day": {
    "2026-06-17": ["08:00", "09:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
  }
}
```

Слоты учитывают **исключения расписания** и **существующие записи** (`appointments`). При указании `service_id` занятость считается как `buffer_before + duration + buffer_after` (время начала услуги — выбранный слот). Буферы фиксируются в записи на момент создания

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
11. GET  /companies/{id}/dashboard?month=2026-06          (статистика за месяц)
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
