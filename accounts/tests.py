from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class AccountTests(TestCase):
    def test_registration_creates_owner_profile_and_logs_in(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newshop",
            "first_name": "Ravi",
            "last_name": "Kumar",
            "email": "ravi@example.com",
            "phone": "9876543210",
            "shop_name": "Ravi Kirana",
            "address": "Main Bazaar",
            "password1": "StrongPass#2026",
            "password2": "StrongPass#2026",
        })
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)
        user = User.objects.get(username="newshop")
        self.assertEqual(user.profile.role, Profile.OWNER)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_phone_must_have_ten_digits(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "badphone", "email": "a@example.com", "phone": "123",
            "shop_name": "X", "address": "Y",
            "password1": "StrongPass#2026", "password2": "StrongPass#2026",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="badphone").exists())

    def test_dashboard_redirects_by_role(self):
        officer = User.objects.create_user("off", password="pass12345")
        Profile.objects.create(user=officer, role=Profile.OFFICER)
        self.client.login(username="off", password="pass12345")
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(response, reverse("verification:officer_dashboard"),
                             fetch_redirect_response=False)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
