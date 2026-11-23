from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile, phone_validator


class RegistrationForm(UserCreationForm):
    """Shopkeeper sign-up: user account + profile details in one form."""

    email = forms.EmailField(required=True)
    phone = forms.CharField(
        max_length=10, validators=[phone_validator], help_text="10-digit mobile number"
    )
    shop_name = forms.CharField(max_length=120, label="Shop or business name")
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))

    field_order = [
        "username", "first_name", "last_name", "email",
        "phone", "shop_name", "address", "password1", "password2",
    ]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.save()
        Profile.objects.update_or_create(
            user=user,
            defaults={
                "role": Profile.OWNER,
                "phone": self.cleaned_data["phone"],
                "shop_name": self.cleaned_data["shop_name"],
                "address": self.cleaned_data["address"],
            },
        )
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("phone", "shop_name", "address")
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
