from django.contrib import admin

from .models import Application, Certificate, Document, Inspection, Notification, Payment


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("reference", "instrument", "applicant", "status", "officer", "created_at")
    list_filter = ("status", "instrument__category")
    search_fields = ("reference", "instrument__serial_number", "applicant__username")
    readonly_fields = ("reference", "created_at", "updated_at")
    inlines = [DocumentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "application", "amount", "method", "paid_at")


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ("application", "officer", "inspected_on", "reference_value", "observed_value", "permissible_error")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("number", "application", "issued_on", "valid_until", "issued_by")
    search_fields = ("number",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read",)
