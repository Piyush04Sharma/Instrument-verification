from django import forms
from django.utils import timezone

from .models import Instrument


class InstrumentForm(forms.ModelForm):
    class Meta:
        model = Instrument
        fields = [
            "category", "make", "model_number", "serial_number", "capacity", "unit",
            "accuracy_class", "year_of_manufacture", "location_of_use",
        ]

    def clean_serial_number(self):
        return self.cleaned_data["serial_number"].strip().upper()

    def clean_year_of_manufacture(self):
        year = self.cleaned_data["year_of_manufacture"]
        this_year = timezone.localdate().year
        if year < 1980 or year > this_year:
            raise forms.ValidationError(f"Enter a year between 1980 and {this_year}.")
        return year
