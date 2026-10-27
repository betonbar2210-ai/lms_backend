from rest_framework.permissions import SAFE_METHODS, BasePermission

MODERATOR_GROUP = "Модераторы"


def is_moderator(user):
    """Проверяет, состоит ли пользователь в группе модераторов."""
    return bool(
        user
        and user.is_authenticated
        and user.groups.filter(name=MODERATOR_GROUP).exists()
    )


class IsModerator(BasePermission):
    message = "Доступ только для модераторов."

    def has_permission(self, request, view):
        return is_moderator(request.user)


class IsNotModerator(BasePermission):
    """Запрещает создание и удаление модераторам.

    Неавторизованным пользователям доступ тоже закрыт: иначе проверка
    "не модератор" пропускала бы анонимов.
    """

    message = "Создавать и удалять объекты может только авторизованный пользователь."

    def has_permission(self, request, view):
        return request.user.is_authenticated and not is_moderator(request.user)


class IsOwnerOrModerator(BasePermission):
    """Читать может любой авторизованный, изменять — владелец или модератор."""

    message = "Изменять и удалять можно только свои объекты."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return is_moderator(request.user) or obj.owner_id == request.user.id


class IsSelfOrReadOnly(BasePermission):
    """Просматривать можно любой профиль, изменять — только свой."""

    message = "Редактировать и удалять можно только свой профиль."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj == request.user
