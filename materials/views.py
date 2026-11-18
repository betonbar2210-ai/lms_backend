from datetime import timedelta

from django.utils import timezone
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated

from materials.models import Course, Material
from materials.paginators import MyPagination
from materials.serializers import (CourseDetailSerializer, CourseSerializer,
                                   MaterialSerializer)
from materials.tasks import send_course_update_notification
from users.permissions import IsNotModerator, IsOwnerOrModerator, is_moderator


class OwnerQuerysetMixin:
    """Ограничивает выборку объектами текущего пользователя.

    Модераторы видят все объекты, остальные — только созданные ими.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return queryset.none()
        if is_moderator(user):
            return queryset
        return queryset.filter(owner=user)


class CourseViewSet(OwnerQuerysetMixin, viewsets.ModelViewSet):
    """Просмотр, Создание, Удаление, Редактирование Курсов"""

    queryset = Course.objects.select_related("owner").order_by("id")
    serializer_class = CourseSerializer
    pagination_class = MyPagination

    def get_queryset(self):
        # Читать курсы может любой авторизованный пользователь,
        # изменять и удалять — только владелец (или модератор).
        if self.action in ("list", "retrieve"):
            queryset = Course.objects.select_related("owner").order_by("id")
            user = getattr(self.request, "user", None)
            if not user or not user.is_authenticated:
                return queryset.none()
            return queryset
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseSerializer

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = [IsAuthenticated, IsNotModerator]
        elif self.action == "destroy":
            self.permission_classes = [
                IsAuthenticated,
                IsNotModerator,
                IsOwnerOrModerator,
            ]
        elif self.action in ("update", "partial_update"):
            self.permission_classes = [IsAuthenticated, IsOwnerOrModerator]
        else:
            self.permission_classes = [IsAuthenticated]
        return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        course = serializer.save()
        send_course_update_notification.delay(course.pk)


class MaterialCreateAPIView(generics.CreateAPIView):
    """Создание Материала"""

    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated, IsNotModerator]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MaterialListAPIView(OwnerQuerysetMixin, generics.ListAPIView):
    """Просмотр всех Материалов"""

    serializer_class = MaterialSerializer
    queryset = Material.objects.select_related("owner").order_by("id")
    permission_classes = [IsAuthenticated]
    pagination_class = MyPagination


class MaterialRetrieveAPIView(OwnerQuerysetMixin, generics.RetrieveAPIView):
    """Просмотр материала"""

    serializer_class = MaterialSerializer
    queryset = Material.objects.select_related("owner").all()
    permission_classes = [IsAuthenticated]


class MaterialUpdateAPIView(OwnerQuerysetMixin, generics.UpdateAPIView):
    """Редактирование Материала"""

    serializer_class = MaterialSerializer
    queryset = Material.objects.select_related("owner").all()
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]

    def perform_update(self, serializer):
        material = serializer.save()
        course = material.course
        now = timezone.now()
        # Уведомляем подписчиков, только если курс не обновлялся более 4 часов
        if now - course.updated_at > timedelta(hours=4):
            Course.objects.filter(pk=course.pk).update(updated_at=now)
            send_course_update_notification.delay(course.pk)


class MaterialDestroyAPIView(OwnerQuerysetMixin, generics.DestroyAPIView):
    """Удаление Материала"""

    serializer_class = MaterialSerializer
    queryset = Material.objects.select_related("owner").all()
    permission_classes = [IsAuthenticated, IsNotModerator, IsOwnerOrModerator]
