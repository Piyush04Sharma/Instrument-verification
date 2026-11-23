import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from instruments.models import Instrument

from .validators import validate_document


class Application(models.Model):
    """A request to verify one instrument. Moves through the statuses below."""

    PENDING_PAYMENT = "pending_payment"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SCHEDULED = "scheduled"
    INSPECTED = "inspected"
    CERTIFIED = "certified"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (PENDING_PAYMENT, "Awaiting payment"),
        (SUBMITTED, "Submitted"),
        (UNDER_REVIEW, "Under review"),
        (SCHEDULED, "Inspection scheduled"),
        (INSPECTED, "Inspected"),
        (CERTIFIED, "Certificate issued"),
        (REJECTED, "Rejected"),
    ]
    FLOW = [PENDING_PAYMENT, SUBMITTED, UNDER_REVIEW, SCHEDULED, INSPECTED, CERTIFIED]
    ACTIVE_STATUSES = [PENDING_PAYMENT, SUBMITTED, UNDER_REVIEW, SCHEDULED, INSPECTED]

    reference = models.CharField(max_length=24, unique=True, editable=False, blank=True)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING_PAYMENT)
    fee = models.DecimalField(max_digits=8, decimal_places=2)
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assigned_applications",
    )
    inspection_date = models.DateField(null=True, blank=True)
    inspection_note = models.CharField(max_length=200, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._make_reference()
        super().save(*args, **kwargs)

    @staticmethod
    def _make_reference():
        while True:
            ref = f"APP-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:5].upper()}"
            if not Application.objects.filter(reference=ref).exists():
                return ref

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    def progress(self):
        """Steps for the progress list on the detail page."""
        labels = dict(self.STATUS_CHOICES)
        index = self.FLOW.index(self.status) if self.status in self.FLOW else None
        steps = []
        for i, key in enumerate(self.FLOW):
            if index is None:
                state = "todo"
            elif i < index or (i == index and self.status == self.CERTIFIED):
                state = "done"
            elif i == index:
                state = "current"
            else:
                state = "todo"
            steps.append({"label": labels[key], "state": state})
        return steps


class Document(models.Model):
    LICENCE = "licence"
    ID_PROOF = "id_proof"
    PREVIOUS = "previous_certificate"
    OTHER = "other"
    TYPE_CHOICES = [
        (LICENCE, "Shop or trade licence"),
        (ID_PROOF, "Owner ID proof"),
        (PREVIOUS, "Previous verification certificate"),
        (OTHER, "Other"),
    ]

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField("Document type", max_length=24, choices=TYPE_CHOICES)
    file = models.FileField(upload_to="documents/%Y/%m/", validators=[validate_document])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_doc_type_display()} for {self.application}"


class Payment(models.Model):
    """Simulated payment: a real gateway can replace the view later."""

    METHOD_CHOICES = [("upi", "UPI"), ("card", "Debit or credit card"), ("netbanking", "Net banking")]

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    method = models.CharField(max_length=12, choices=METHOD_CHOICES)
    transaction_id = models.CharField(max_length=20, unique=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transaction_id


class Inspection(models.Model):
    """Readings taken by the officer. A scale or meter passes when the observed value
    is within the permissible error of the reference value."""

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="inspection")
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="inspections"
    )
    inspected_on = models.DateField()
    reference_value = models.DecimalField(
        max_digits=10, decimal_places=3, help_text="Value of the standard weight or measure used"
    )
    observed_value = models.DecimalField(
        max_digits=10, decimal_places=3, help_text="Value shown by the instrument"
    )
    permissible_error = models.DecimalField(max_digits=10, decimal_places=3)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inspection of {self.application}"

    @property
    def error(self):
        return abs(self.observed_value - self.reference_value)

    @property
    def within_tolerance(self):
        return self.error <= self.permissible_error


class Certificate(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="certificate")
    number = models.CharField(max_length=20, unique=True)
    issued_on = models.DateField()
    valid_until = models.DateField()
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="issued_certificates"
    )

    class Meta:
        ordering = ["-issued_on", "-id"]

    def __str__(self):
        return self.number

    @property
    def is_valid(self):
        return self.valid_until >= timezone.localdate()

    @property
    def state(self):
        """valid, expiring (within 30 days) or expired."""
        today = timezone.localdate()
        if self.valid_until < today:
            return "expired"
        if self.valid_until <= today + timedelta(days=30):
            return "expiring"
        return "valid"

    @property
    def state_label(self):
        return {"valid": "Valid", "expiring": "Expires soon", "expired": "Expired"}[self.state]


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.message
