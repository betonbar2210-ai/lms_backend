from django.urls import path
from rest_framework.routers import DefaultRouter

from materials.apps import MaterialsConfig
from materials.views import (
    CourseViewSet,
    MaterialCreateAPIView,
    MaterialDestroyAPIView,
    MaterialListAPIView,
    MaterialRetrieveAPIView,
    MaterialUpdateAPIView,
)

app_name = MaterialsConfig.name

router = DefaultRouter()
router.register("", CourseViewSet, basename="courses")

urlpatterns = [
    path("materials/create/", MaterialCreateAPIView.as_view(), name="create"),
    path("materials/", MaterialListAPIView.as_view(), name="list"),
    path("materials/<int:pk>/", MaterialRetrieveAPIView.as_view(), name="retrieve"),
    path("materials/update/<int:pk>/", MaterialUpdateAPIView.as_view(), name="update"),
    path("materials/delete/<int:pk>/", MaterialDestroyAPIView.as_view(), name="delete"),
] + router.urls
