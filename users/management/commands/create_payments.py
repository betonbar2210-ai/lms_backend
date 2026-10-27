from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from materials.models import Course, Material
from users.models import Payments

User = get_user_model()


class Command(BaseCommand):
    help = "Создаёт тестовые платежи для пользователей"

    def handle(self, *args, **kwargs):
        user1, _ = User.objects.get_or_create(
            email="ivanov@example.com",
            defaults={"phone": "+79001234567", "city": "Москва", "is_active": True},
        )
        user2, _ = User.objects.get_or_create(
            email="petrov@example.com",
            defaults={
                "phone": "+79007654321",
                "city": "Санкт-Петербург",
                "is_active": True,
            },
        )
        course1 = Course.objects.first()
        course2 = Course.objects.last()
        lesson1 = Material.objects.first()

        if not course1 or not lesson1:
            self.stdout.write(self.style.ERROR("Сначала создайте курсы и уроки!"))
            return

        payments_data = [
            {
                "user": user1,
                "course": course1,
                "lesson": None,
                "total": 5000.00,
                "method": "cash",
            },
            {
                "user": user2,
                "course": None,
                "lesson": lesson1,
                "total": 1500.50,
                "method": "transfer",
            },
            {
                "user": user1,
                "course": course2,
                "lesson": None,
                "total": 7500.00,
                "method": "transfer",
            },
        ]

        created_count = 0
        for data in payments_data:
            payment, created = Payments.objects.get_or_create(
                user=data["user"],
                course=data.get("course"),
                lesson=data.get("lesson"),
                defaults={
                    "total": data["total"],
                    "method": data["method"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Создан платёж: {payment}"))

        self.stdout.write(
            self.style.SUCCESS(f"\nВсего создано платежей: {created_count}")
        )
