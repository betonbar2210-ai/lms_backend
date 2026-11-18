from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("courses/", include("materials.urls", namespace="courses")),
    path("users/", include("users.urls", namespace="users")),
    # --- Документация API ---
    # Эндпоинт, который отдает схему OpenAPI в формате JSON или YAML
    path("docs/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI - красивая и удобная документация
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Redoc - альтернативный вариант документации
    path("docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
