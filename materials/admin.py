from django.contrib import admin

from materials.models import Course, Material


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner")
    list_filter = ("owner",)
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "course", "owner")
    list_filter = ("course", "owner")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)
