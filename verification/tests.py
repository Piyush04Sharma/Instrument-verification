import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from instruments.models import Category, Instrument

from .models import Application, Certificate, Inspection
from .utils import add_months

TEMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class WorkflowTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Weighing scale", verification_fee=Decimal("500"), validity_months=12
        )
        self.owner = User.objects.create_user("shop", password="pass12345", email="shop@example.com")
        Profile.objects.create(user=self.owner, role=Profile.OWNER, shop_name="Test Shop")
        self.officer = User.objects.create_user("officer", password="pass12345")
        Profile.objects.create(user=self.officer, role=Profile.OFFICER)
        self.instrument = Instrument.objects.create(
            owner=self.owner, category=self.category, make="Essae", model_number="DS-252",
            serial_number="SN100", capacity=Decimal("30"), unit="kg", accuracy_class="III",
            year_of_manufacture=2022, location_of_use="Main Bazaar",
        )
        self.owner_client = self.client_class()
        self.owner_client.login(username="shop", password="pass12345")
        self.officer_client = self.client_class()
        self.officer_client.login(username="officer", password="pass12345")

    def _submit_application(self):
        upload = SimpleUploadedFile("licence.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = self.owner_client.post(reverse("verification:apply"), {
            "instrument": self.instrument.pk, "doc_type": "licence", "document": upload,
        })
        app = Application.objects.get()
        self.assertRedirects(response, reverse("verification:pay", args=[app.pk]))
        self.owner_client.post(reverse("verification:pay", args=[app.pk]), {"method": "upi"})
        app.refresh_from_db()
        return app

    def _inspect(self, app, observed):
        self.officer_client.post(reverse("verification:officer_start_review", args=[app.pk]))
        self.officer_client.post(reverse("verification:officer_schedule", args=[app.pk]), {
            "inspection_date": (timezone.localdate() + timedelta(days=3)).isoformat(),
            "note": "Shop visit",
        })
        self.officer_client.post(reverse("verification:officer_inspect", args=[app.pk]), {
            "inspected_on": timezone.localdate().isoformat(),
            "reference_value": "10", "observed_value": observed, "permissible_error": "0.01",
            "remarks": "",
        })
        app.refresh_from_db()

    def test_full_flow_ends_with_valid_public_certificate(self):
        app = self._submit_application()
        self.assertEqual(app.status, Application.SUBMITTED)
        self.assertEqual(app.payment.amount, Decimal("500"))

        self._inspect(app, "10.005")
        self.assertEqual(app.status, Application.INSPECTED)

        self.officer_client.post(reverse("verification:officer_approve", args=[app.pk]))
        app.refresh_from_db()
        self.assertEqual(app.status, Application.CERTIFIED)
        certificate = Certificate.objects.get(application=app)
        self.assertEqual(
            certificate.valid_until, add_months(timezone.localdate(), self.category.validity_months)
        )

        # Anyone can check the certificate without logging in.
        response = self.client.get(reverse("verification:verify_number", args=[certificate.number]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["state"], "valid")

        # The owner can download the PDF.
        pdf = self.owner_client.get(reverse("verification:certificate_pdf", args=[certificate.number]))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_certificate_is_refused_when_readings_are_out_of_tolerance(self):
        app = self._submit_application()
        self._inspect(app, "10.500")
        self.officer_client.post(reverse("verification:officer_approve", args=[app.pk]))
        app.refresh_from_db()
        self.assertEqual(app.status, Application.INSPECTED)
        self.assertFalse(Certificate.objects.exists())

    def test_rejection_and_resubmission(self):
        app = self._submit_application()
        self.officer_client.post(reverse("verification:officer_reject", args=[app.pk]), {
            "reason": "The licence scan is not readable.",
        })
        app.refresh_from_db()
        self.assertEqual(app.status, Application.REJECTED)
        self.owner_client.post(reverse("verification:resubmit", args=[app.pk]))
        app.refresh_from_db()
        self.assertEqual(app.status, Application.SUBMITTED)

    def test_wrong_file_type_is_rejected(self):
        upload = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
        response = self.owner_client.post(reverse("verification:apply"), {
            "instrument": self.instrument.pk, "doc_type": "licence", "document": upload,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Application.objects.exists())

    def test_roles_are_enforced(self):
        self.assertEqual(self.owner_client.get(reverse("verification:officer_dashboard")).status_code, 403)
        self.assertEqual(self.officer_client.get(reverse("verification:owner_dashboard")).status_code, 403)
        self.assertEqual(self.officer_client.get(reverse("verification:admin_dashboard")).status_code, 403)
        anonymous = self.client.get(reverse("verification:officer_dashboard"))
        self.assertEqual(anonymous.status_code, 302)

    def test_unknown_certificate_number(self):
        response = self.client.get(reverse("verification:verify"), {"number": "lm-0000-zzzzzz"})
        self.assertEqual(response.context["state"], "not_found")

    def test_add_months_clips_to_month_end(self):
        from datetime import date
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 11, 23), 12), date(2027, 11, 23))
