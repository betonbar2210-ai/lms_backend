from django.urls import path
from rest_framework import routers

from users.apps import UsersConfig
from users.views import UsersViewSet

app_name = UsersConfig.name


router = routers.DefaultRouter()
router.register(r"users", UsersViewSet, basename="users")


urlpatterns = [] + router.urls
