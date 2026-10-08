from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = PhoneNumberField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-id']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
