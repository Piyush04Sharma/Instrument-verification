from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    """A kind of instrument, with its verification fee and certificate validity."""

    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    verification_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("500.00"))
    validity_months = models.PositiveSmallIntegerField(
        default=12, help_text="How many months a certificate stays valid"
    )

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Instrument(models.Model):
    UNIT_CHOICES = [
        ("kg", "Kilogram"),
        ("g", "Gram"),
        ("l", "Litre"),
        ("ml", "Millilitre"),
        ("m", "Metre"),
    ]
    ACCURACY_CHOICES = [
        ("I", "Class I (special)"),
        ("II", "Class II (high)"),
        ("III", "Class III (medium)"),
        ("IIII", "Class IIII (ordinary)"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instruments"
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="instruments")
    make = models.CharField("Manufacturer", max_length=80)
    model_number = models.CharField(max_length=60)
    serial_number = models.CharField(
        max_length=60,
        unique=True,
        error_messages={"unique": "An instrument with this serial number is already registered."},
    )
    capacity = models.DecimalField(
        max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))]
    )
    unit = models.CharField(max_length=3, choices=UNIT_CHOICES, default="kg")
    accuracy_class = models.CharField(max_length=4, choices=ACCURACY_CHOICES, default="III")
    year_of_manufacture = models.PositiveSmallIntegerField()
    location_of_use = models.CharField(max_length=200, help_text="Shop or site where it is used")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.make} {self.model_number} ({self.serial_number})"

    @property
    def is_locked(self):
        """Instruments that already have applications can no longer be edited or deleted."""
        return self.applications.exists()

    def latest_certificate(self):
        from verification.models import Certificate

        return (
            Certificate.objects.filter(application__instrument=self)
            .order_by("-issued_on", "-id")
            .first()
        )

    def latest_application(self):
        return self.applications.order_by("-created_at", "-id").first()
