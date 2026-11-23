import uuid

from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile

from .models import Certificate, Notification
from .utils import add_months


def notify(user, message, url=""):
    """Store an in-app notification and send an email (printed in the terminal in development)."""
    Notification.objects.create(user=user, message=message[:255], url=url)
    if user.email:
        send_mail("Instrument verification update", message, None, [user.email], fail_silently=True)


def notify_officers(message, url=""):
    for profile in Profile.objects.filter(role=Profile.OFFICER).select_related("user"):
        notify(profile.user, message, url)


def _make_certificate_number(year):
    while True:
        number = f"LM-{year}-{uuid.uuid4().hex[:6].upper()}"
        if not Certificate.objects.filter(number=number).exists():
            return number


@transaction.atomic
def issue_certificate(application, officer):
    today = timezone.localdate()
    months = application.instrument.category.validity_months
    certificate = Certificate.objects.create(
        application=application,
        number=_make_certificate_number(today.year),
        issued_on=today,
        valid_until=add_months(today, months),
        issued_by=officer,
    )
    application.status = application.CERTIFIED
    application.save(update_fields=["status", "updated_at"])
    notify(
        application.applicant,
        f"Certificate {certificate.number} has been issued for {application.instrument}.",
        reverse("verification:application_detail", args=[application.pk]),
    )
    return certificate
