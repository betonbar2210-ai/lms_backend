from django.urls import path

from materials.apps import MaterialsConfig
from materials.views import CourseViewSet, MaterialCreateAPIView, MaterialRetrieveAPIView, MaterialUpdateAPIView, \
    MaterialDestroyAPIView
from rest_framework.routers import DefaultRouter

app_name = MaterialsConfig.name

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='courses')

urlpatterns = [
    path('create/', MaterialCreateAPIView.as_view(), name='create'),
    path('', MaterialCreateAPIView.as_view(), name='list'),
    path('<pk:int>/', MaterialRetrieveAPIView.as_view(), name='retrieve'),
    path('update/<pk:int>/', MaterialUpdateAPIView.as_view(), name='update'),
    path('delete/<pk:int>/', MaterialDestroyAPIView.as_view(), name='delete'),
] + router.urls
