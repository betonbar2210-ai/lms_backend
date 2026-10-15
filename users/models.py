from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("У суперпользователя is_staff должен быть True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("У суперпользователя is_superuser должен быть True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    phone = PhoneNumberField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-id"]

    def __str__(self):
        return self.email


class Payments(models.Model):
    PAYMENT_METHODS = [
        ("cash", "Наличными"),
        ("transfer", "Перевод на счет"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    lesson = models.ForeignKey("materials.Material", on_delete=models.CASCADE, blank=True, null=True, related_name="payment_material")
    course = models.ForeignKey("materials.Course", on_delete=models.CASCADE, blank=True, null=True, related_name="payment_course")
    method = models.CharField(max_length=50, choices=PAYMENT_METHODS)

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
        ordering = ["-date"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(course__isnull=False, lesson__isnull=True)
                    | models.Q(course__isnull=True, lesson__isnull=False)
                ),
                name="payment_course_xor_lesson",
            )
        ]

    def __str__(self):
        if self.course:
            paid_for = self.course.name
        elif self.lesson:
            paid_for = self.lesson.name
        else:
            paid_for = "Не указано"
        return f"{self.user.email} - {paid_for} ({self.total} руб.)"
