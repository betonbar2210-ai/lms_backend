from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

from users.apps import UsersConfig
from users.views import (
    MyTokenObtainPairView,
    PaymentViewSet,
    UserRegisterAPIView,
    UsersViewSet,
)

app_name = UsersConfig.name


users_router = routers.DefaultRouter()
users_router.register("", UsersViewSet, basename="users")

payments_router = routers.DefaultRouter()
payments_router.register("", PaymentViewSet, basename="payments")


urlpatterns = [
    path("register/", UserRegisterAPIView.as_view(), name="register"),
    path("token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("payments/", include(payments_router.urls)),
] + users_router.urls
