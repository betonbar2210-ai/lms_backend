from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from materials.models import Course, Material

MODERATOR_GROUP = "Модераторы"


class Command(BaseCommand):
    help = (
        "Создаёт группу Модераторы и выдаёт права "
        "на просмотр и изменение курсов и уроков"
    )

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name=MODERATOR_GROUP)

        for model in (Course, Material):
            content_type = ContentType.objects.get_for_model(model)
            for action in ("view", "change"):
                permission = Permission.objects.get(
                    content_type=content_type,
                    codename=f"{action}_{model._meta.model_name}",
                )
                group.permissions.add(permission)

        self.stdout.write(
            self.style.SUCCESS(f"{'Создана' if created else 'Уже есть'}: {group.name}")
        )
