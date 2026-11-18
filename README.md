# LMS Backend

REST API учебной платформы на Django REST Framework: курсы и материалы, пользователи,
платежи через Stripe и подписки на обновления курсов.

## Стек и поддерживаемые версии

| Компонент | Версия |
|---|---|
| **Python** | **3.12 – 3.14** (проверено на 3.14.4) |
| Django | 6.1.1 |
| Django REST Framework | 3.18.1 |
| djangorestframework-simplejwt | 5.5.1 |
| django-filter | 26.2 |
| drf-spectacular | 0.30.0 |
| Stripe SDK | 16.1.0 |
| PostgreSQL / psycopg2-binary | 2.9.13 |
| Pillow | 12.3.0 |

> **Важно:** Django 6.1 требует **Python >= 3.12** (`Requires-Python: >=3.12`) и
> официально поддерживает CPython 3.12, 3.13 и 3.14. На Python 3.11 и ниже проект
> не запустится — при развёртывании используйте интерпретатор не старше 3.12.

## Установка

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Скопируйте `.env.example` в `.env` и заполните переменные (полный список — в `.env.example`):

```dotenv
DATABASE_NAME=...
DATABASE_USER=...
DATABASE_PASSWORD=...
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432

SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Stripe (ключ начинается с sk_test_)
STRIPE_TEST_KEY=sk_test_...
STRIPE_CURRENCY=rub

# Celery / Redis
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Email / SMTP
# Для разработки по умолчанию используется консольный backend (письма выводятся в лог).
# Для реальной отправки укажите SMTP-настройки:
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=noreply@lms.local
```

Примените миграции и запустите сервер:

```bash
python manage.py migrate
python manage.py check
python manage.py runserver
```

## Документация API

Документация генерируется через **drf-spectacular** и доступна после запуска сервера:

| Адрес | Назначение |
|---|---|
| `/docs/` | Swagger UI |
| `/docs/redoc/` | ReDoc |
| `/docs/schema/` | OpenAPI-схема (JSON/YAML) |

В Swagger можно авторизоваться по JWT: получите токен через `POST /users/token/`,
нажмите **Authorize** и вставьте `access`-токен.

Схема также сохранена в репозитории в файле `schema.yaml`. Чтобы обновить её после
изменения API:

```bash
python manage.py spectacular --validate --file schema.yaml
```

Команда с `--validate` завершается с ненулевым кодом, если в схеме есть ошибки —
удобно использовать в CI.

## Платежи через Stripe

Платёж создаётся запросом:

```http
POST /users/payments/create/
Authorization: Bearer <access>
Content-Type: application/json

{"course_id": 1}
```

или `{"lesson_id": 1}` — необходимо указать **ровно один** из идентификаторов.

Сервер:

1. создаёт продукт (`stripe.Product.create`);
2. создаёт цену в копейках (`stripe.Price.create`, `unit_amount = price * 100`);
3. создаёт сессию оплаты (`stripe.checkout.Session.create`);
4. сохраняет в `Payments` все данные Stripe: `stripe_product_id`, `stripe_price_id`,
   `stripe_session_id`, `stripe_payment_url` и статус `pending`;
5. возвращает `url` страницы оплаты, `session_id` и `payment_id`.

После оплаты Stripe перенаправляет пользователя на:

- `GET /users/payments/success/?session_id=...` — статус сессии проверяется напрямую
  в Stripe и синхронизируется с моделью (`paid`, `no_payment_required` → `paid`,
  `unpaid` → `pending`);
- `GET /users/payments/cancel/?session_id=...` — платёж переводится в `canceled`,
  если он ещё не был оплачен.

Оба обработчика доступны без JWT (`AllowAny`), потому что Stripe открывает их
в браузере пользователя без заголовка `Authorization`.

### Ограничения реализации

Статус синхронизируется только при возврате пользователя на `success_url`.
Если пользователь закрыл вкладку, платёж может остаться в `pending`, хотя Stripe
уже получил оплату. Для production-сценария нужен webhook на
`checkout.session.completed` с проверкой подписи (`stripe.Webhook.construct_event`).

## Celery

В проекте настроен Celery с брокером Redis (`config/celery.py`, настройки в
`config/settings.py`). Для работы нужен запущенный Redis.

Запуск воркера:

```bash
# Linux / macOS
celery -A config worker -l info

# Windows (prefork недоступен, используется eventlet)
celery -A config worker -l info -P eventlet
```

Проверка, что Celery видит задачи:

```bash
celery -A config inspect registered
```

Для быстрой проверки конфигурации без Redis можно вызвать тестовую задачу в
eager-режиме:

```bash
python manage.py shell -c "from config.celery import debug_task; from django.conf import settings; settings.CELERY_TASK_ALWAYS_EAGER=True; debug_task.delay()"
```

## Тесты

```bash
python manage.py test
```

Тесты платежей подменяют вызовы Stripe через `unittest.mock.patch`, поэтому реальные
запросы к Stripe и интернет не нужны. Покрыты создание продукта/цены/сессии,
сохранение всех Stripe-идентификаторов, ошибка Stripe без создания платежа,
синхронизация `paid`, отмена в `canceled` и XOR-валидация `course_id`/`lesson_id`.

## Форматирование

```bash
black users materials config
isort users materials config
```
