# LMS Backend

REST API учебной платформы на Django REST Framework: курсы и материалы, пользователи,
платежи и подписки на обновления курсов.

## Стек и поддерживаемые версии

| Компонент | Версия |
|---|---|
| **Python** | **3.12 – 3.14** (проверено на 3.14.4) |
| Django | 6.1.1 |
| Django REST Framework | 3.18.1 |
| djangorestframework-simplejwt | 5.5.1 |
| django-filter | 26.2 |
| PostgreSQL / psycopg2-binary | 2.9.13 |
| Pillow | 12.3.0 |

> **Важно:** Django 6.1 требует **Python >= 3.12** (`Requires-Python: >=3.12`) и
> официально поддерживает CPython 3.12, 3.13 и 3.14. На Python 3.11 и ниже проект
> не запустится — при развёртывании используйте интерпретатор не старше 3.12.
