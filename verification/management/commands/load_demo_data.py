from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile
from instruments.models import Category, Instrument
from verification.models import Application, Inspection, Payment
from verification.services import issue_certificate


class Command(BaseCommand):
    help = "Creates demo categories, groups, users, instruments and a few applications."

    def handle(self, *args, **options):
        self.make_categories()
        owners, officers, admins = self.make_groups()
        admin = self.make_user("admin", "admin123", Profile.ADMIN, admins, "Site", "Admin", superuser=True)
        officer = self.make_user("officer1", "officer123", Profile.OFFICER, officers, "Anita", "Sharma")
        owner = self.make_user(
            "shop1", "shop123", Profile.OWNER, owners, "Ravi", "Kumar",
            shop_name="Ravi Kirana Store", address="12 Main Bazaar", phone="9876543210",
        )
        self.make_applications(owner, officer)
        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write("  Administrator: admin / admin123")
        self.stdout.write("  Officer:       officer1 / officer123")
        self.stdout.write("  Shopkeeper:    shop1 / shop123")

    def make_categories(self):
        rows = [
            ("Weighing scale", "Platform, counter and spring balances", "500.00", 12),
            ("Fuel dispenser meter", "Petrol and diesel dispensing meters", "1500.00", 12),
            ("Measuring tape", "Length measures and tapes", "200.00", 24),
            ("Weights", "Standard weights and weight sets", "300.00", 24),
            ("Liquid measure", "Measuring jars and milk measures", "250.00", 24),
        ]
        for name, desc, fee, months in rows:
            Category.objects.get_or_create(
                name=name,
                defaults={"description": desc, "verification_fee": Decimal(fee), "validity_months": months},
            )

    def make_groups(self):
        """Groups and permissions (syllabus Unit V)."""
        def perms(*codenames):
            return Permission.objects.filter(codename__in=codenames)

        owners, _ = Group.objects.get_or_create(name="Shopkeepers")
        owners.permissions.set(perms(
            "add_instrument", "change_instrument", "view_instrument",
            "add_application", "view_application", "add_document", "view_document",
        ))
        officers, _ = Group.objects.get_or_create(name="Inspection officers")
        officers.permissions.set(perms(
            "view_instrument", "view_application", "change_application", "view_document",
            "add_inspection", "change_inspection", "view_inspection",
            "add_certificate", "view_certificate",
        ))
        admins, _ = Group.objects.get_or_create(name="Administrators")
        admins.permissions.set(Permission.objects.filter(
            content_type__app_label__in=["accounts", "instruments", "verification"]
        ))
        return owners, officers, admins

    def make_user(self, username, password, role, group, first, last, superuser=False, **profile_fields):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"first_name": first, "last_name": last, "email": f"{username}@example.com"},
        )
        if created:
            user.set_password(password)
        if superuser:
            user.is_staff = True
            user.is_superuser = True
        user.save()
        user.groups.add(group)
        Profile.objects.update_or_create(user=user, defaults={"role": role, **profile_fields})
        return user

    def make_applications(self, owner, officer):
        if Instrument.objects.filter(owner=owner).exists():
            return
        scale = Category.objects.get(name="Weighing scale")
        meter = Category.objects.get(name="Fuel dispenser meter")
        verified = Instrument.objects.create(
            owner=owner, category=scale, make="Essae", model_number="DS-252", serial_number="ESS-2201",
            capacity=Decimal("30"), unit="kg", accuracy_class="III", year_of_manufacture=2022,
            location_of_use="Counter, Ravi Kirana Store",
        )
        waiting = Instrument.objects.create(
            owner=owner, category=scale, make="Avery", model_number="Spring-10", serial_number="AVR-0915",
            capacity=Decimal("10"), unit="kg", accuracy_class="IIII", year_of_manufacture=2020,
            location_of_use="Vegetable stall",
        )
        Instrument.objects.create(
            owner=owner, category=meter, make="Gilbarco", model_number="Encore", serial_number="GIL-7788",
            capacity=Decimal("99.999"), unit="l", accuracy_class="II", year_of_manufacture=2021,
            location_of_use="Highway fuel point",
        )

        # One finished application with a certificate
        done = Application.objects.create(
            instrument=verified, applicant=owner, fee=scale.verification_fee, officer=officer,
            status=Application.INSPECTED, inspection_date=timezone.localdate() - timedelta(days=2),
        )
        Payment.objects.create(
            application=done, amount=done.fee, method="upi", transaction_id="TXNDEMO000001",
        )
        Inspection.objects.create(
            application=done, officer=officer, inspected_on=timezone.localdate() - timedelta(days=2),
            reference_value=Decimal("10.000"), observed_value=Decimal("10.004"),
            permissible_error=Decimal("0.010"), remarks="Readings within limits.",
        )
        issue_certificate(done, officer)

        # One application waiting for an officer
        pending = Application.objects.create(
            instrument=waiting, applicant=owner, fee=scale.verification_fee, status=Application.SUBMITTED,
        )
        Payment.objects.create(
            application=pending, amount=pending.fee, method="card", transaction_id="TXNDEMO000002",
        )
