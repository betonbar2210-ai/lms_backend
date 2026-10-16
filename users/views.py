from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter

from users.models import Payments, User
from users.serializers import PaymentSerializer, UsersSerializer


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("payments").all()
    serializer_class = UsersSerializer


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payments.objects.all()
    serializer_class = PaymentSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]

    filterset_fields = ("course", "lesson", "method")

    ordering_fields = ("date",)
    ordering = ["-date"]
