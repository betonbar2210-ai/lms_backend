from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import Payments, User


@admin.register(User)
class UsersAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "phone", "city", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "groups")
    search_fields = ("email", "phone", "city")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личные данные", {"fields": ("phone", "city", "avatar")}),
        (
            "Права",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Даты", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


admin.site.register(Payments)
