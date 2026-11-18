from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from users.models import User


@shared_task
def deactivate_inactive_users():
    """Блокирует пользователей, которые не заходили более месяца."""
    threshold = timezone.now() - timedelta(days=30)
    users = User.objects.filter(
        is_active=True,
        is_staff=False,
        is_superuser=False,
        last_login__lt=threshold,
    )
    count = users.update(is_active=False)
    return f"Заблокировано пользователей: {count}"
