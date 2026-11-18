from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from materials.models import Course
from users.models import Subscriptions


@shared_task
def send_course_update_notification(course_id):
    """Отправляет письма подписчикам об обновлении материалов курса."""
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return "Курс не найден"

    emails = list(
        Subscriptions.objects.filter(course=course, user__is_active=True)
        .exclude(user__email="")
        .values_list("user__email", flat=True)
        .distinct()
    )

    if not emails:
        return "Нет подписчиков"

    subject = f'Обновление курса "{course.name}"'
    message = (
        f'Материалы курса "{course.name}" были обновлены. '
        "Зайдите на платформу, чтобы ознакомиться с изменениями."
    )

    for email in emails:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

    return f"Отправлено писем: {len(emails)}"
