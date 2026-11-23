from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(r"^\d{10}$", "Enter a 10-digit mobile number.")


class Profile(models.Model):
    """Extra details and the role of each user (shopkeeper, officer or administrator)."""

    OWNER = "owner"
    OFFICER = "officer"
    ADMIN = "admin"
    ROLE_CHOICES = [
        (OWNER, "Shopkeeper"),
        (OFFICER, "Inspection officer"),
        (ADMIN, "Administrator"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=OWNER)
    phone = models.CharField(max_length=10, blank=True, validators=[phone_validator])
    shop_name = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
