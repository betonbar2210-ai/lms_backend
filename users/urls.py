from rest_framework import routers

from users.apps import UsersConfig
from users.views import PaymentViewSet, UsersViewSet

app_name = UsersConfig.name


router = routers.DefaultRouter()
router.register(r"users", UsersViewSet, basename="users")
router.register(r"payments", PaymentViewSet, basename="payments")


urlpatterns = router.urls
