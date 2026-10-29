from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import Payments, Subscriptions, User
from users.permissions import IsSelfOrReadOnly, is_moderator
from users.serializers import (
    MyTokenObtainPairSerializer,
    PaymentSerializer,
    SubscriptionToggleSerializer,
    UserPrivateSerializer,
    UserRegisterSerializer,
    UsersSerializer,
)


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegisterSerializer
        if self.action == "retrieve" and self.get_object() == self.request.user:
            return UserPrivateSerializer
        return UsersSerializer

    def get_permissions(self):
        # Создавать пользователей может любой авторизованный,
        # просматривать — любой, изменять — только свой профиль.
        if self.action == "create":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSelfOrReadOnly()]

    def get_queryset(self):
        queryset = User.objects.all()
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("payments")
        return queryset


class UserRegisterAPIView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]

    filterset_fields = ("course", "lesson", "method")

    ordering_fields = ("date",)
    ordering = ["-date"]

    def get_queryset(self):
        queryset = Payments.objects.select_related("user", "course", "lesson")
        if is_moderator(self.request.user) or self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)


class SubscriptionsToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubscriptionToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]

        subscription, created = Subscriptions.objects.get_or_create(
            user=request.user,
            course=course,
        )

        if created:
            message = "подписка добавлена"
        else:
            subscription.delete()
            message = "подписка удалена"

        return Response({"message": message})


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = [AllowAny]
