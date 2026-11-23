from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile

from .forms import InstrumentForm
from .models import Category, Instrument


class InstrumentTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Weighing scale", verification_fee=Decimal("500"))
        self.owner = User.objects.create_user("shop", password="pass12345")
        Profile.objects.create(user=self.owner, role=Profile.OWNER)
        self.data = {
            "category": self.category.pk, "make": "Essae", "model_number": "DS-252",
            "serial_number": "sn-100", "capacity": "30", "unit": "kg",
            "accuracy_class": "III", "year_of_manufacture": "2022", "location_of_use": "Main Bazaar",
        }

    def test_serial_number_is_normalised_and_must_be_unique(self):
        form = InstrumentForm(self.data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["serial_number"], "SN-100")
        Instrument.objects.create(
            owner=self.owner, category=self.category, make="X", model_number="Y",
            serial_number="SN-100", capacity=Decimal("1"), unit="kg", accuracy_class="III",
            year_of_manufacture=2020, location_of_use="Shop",
        )
        self.assertFalse(InstrumentForm(self.data).is_valid())

    def test_capacity_must_be_positive_and_year_not_in_future(self):
        bad = dict(self.data, capacity="0", year_of_manufacture="2999")
        form = InstrumentForm(bad)
        self.assertFalse(form.is_valid())
        self.assertIn("capacity", form.errors)
        self.assertIn("year_of_manufacture", form.errors)

    def test_owner_can_add_instrument(self):
        self.client.login(username="shop", password="pass12345")
        response = self.client.post(reverse("instruments:add"), self.data)
        instrument = Instrument.objects.get()
        self.assertEqual(instrument.owner, self.owner)
        self.assertRedirects(response, reverse("instruments:detail", args=[instrument.pk]))

    def test_list_requires_login(self):
        response = self.client.get(reverse("instruments:list"))
        self.assertEqual(response.status_code, 302)
