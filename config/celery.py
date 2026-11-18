import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Загружает настройки Django с префиксом CELERY_ (например, CELERY_BROKER_URL)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически ищет tasks.py во всех INSTALLED_APPS
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Тестовая задача для проверки работы Celery."""
    print(f"Request: {self.request!r}")
