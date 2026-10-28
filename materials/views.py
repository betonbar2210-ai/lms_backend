from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated

from materials.models import Course, Material
from materials.serializers import (
    CourseDetailSerializer,
    CourseSerializer,
    MaterialSerializer,
)
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
    queryset = Course.objects.select_related("owner").all()
    serializer_class = CourseSerializer

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


class MaterialCreateAPIView(generics.CreateAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated, IsNotModerator]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MaterialListAPIView(OwnerQuerysetMixin, generics.ListAPIView):
    serializer_class = MaterialSerializer
    queryset = Material.objects.select_related("owner").all()
    permission_classes = [IsAuthenticated]


class MaterialRetrieveAPIView(OwnerQuerysetMixin, generics.RetrieveAPIView):
    serializer_class = MaterialSerializer
    queryset = Material.objects.select_related("owner").all()
    permission_classes = [IsAuthenticated]


class MaterialUpdateAPIView(OwnerQuerysetMixin, generics.UpdateAPIView):
    serializer_class = MaterialSerializer
    queryset = Material.objects.select_related("owner").all()
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]


class MaterialDestroyAPIView(OwnerQuerysetMixin, generics.DestroyAPIView):
    queryset = Material.objects.select_related("owner").all()
    permission_classes = [IsAuthenticated, IsNotModerator, IsOwnerOrModerator]
