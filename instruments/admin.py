from django.contrib import admin

from .models import Category, Instrument


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "verification_fee", "validity_months")
    search_fields = ("name",)


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ("serial_number", "make", "model_number", "category", "owner", "created_at")
    list_filter = ("category", "accuracy_class", "unit")
    search_fields = ("serial_number", "make", "model_number", "owner__username")
