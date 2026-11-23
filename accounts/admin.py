from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class UserAdmin(BaseUserAdmin):
    """User admin with the role/profile shown on the same page."""

    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "is_staff", "is_active")


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
