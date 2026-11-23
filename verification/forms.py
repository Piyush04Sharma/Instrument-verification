from django import forms
from django.utils import timezone

from instruments.models import Instrument

from .models import Application, Document, Inspection, Payment
from .validators import validate_document


class ApplicationForm(forms.Form):
    """Choose an instrument and upload the supporting documents."""

    instrument = forms.ModelChoiceField(queryset=Instrument.objects.none())
    doc_type = forms.ChoiceField(label="First document", choices=Document.TYPE_CHOICES)
    document = forms.FileField(
        label="Upload first document", validators=[validate_document],
        help_text="PDF, JPG or PNG, up to 2 MB",
    )
    extra_document = forms.FileField(
        label="Second document (optional)", required=False, validators=[validate_document],
    )
    extra_doc_type = forms.ChoiceField(
        label="Second document type", choices=Document.TYPE_CHOICES, required=False,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only this user's instruments that have no application in progress.
        self.fields["instrument"].queryset = (
            Instrument.objects.filter(owner=user)
            .exclude(applications__status__in=Application.ACTIVE_STATUSES)
            .select_related("category")
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("extra_document") and not cleaned.get("extra_doc_type"):
            self.add_error("extra_doc_type", "Choose the type of the second document.")
        return cleaned


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["doc_type", "file"]
        labels = {"file": "File"}


class PaymentForm(forms.Form):
    method = forms.ChoiceField(label="Payment method", choices=Payment.METHOD_CHOICES)


class ScheduleForm(forms.Form):
    inspection_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    note = forms.CharField(
        max_length=200, required=False, label="Venue or instructions",
        help_text="For example: bring the instrument and its standard weights to the shop counter.",
    )

    def clean_inspection_date(self):
        day = self.cleaned_data["inspection_date"]
        if day < timezone.localdate():
            raise forms.ValidationError("The inspection date can't be in the past.")
        return day


class InspectionForm(forms.ModelForm):
    class Meta:
        model = Inspection
        fields = ["inspected_on", "reference_value", "observed_value", "permissible_error", "remarks"]
        widgets = {
            "inspected_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_inspected_on(self):
        day = self.cleaned_data["inspected_on"]
        if day > timezone.localdate():
            raise forms.ValidationError("The inspection date can't be in the future.")
        return day

    def clean(self):
        cleaned = super().clean()
        for name in ("reference_value", "observed_value", "permissible_error"):
            value = cleaned.get(name)
            if value is not None and value < 0:
                self.add_error(name, "Enter zero or a positive number.")
        return cleaned


class RejectForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}), min_length=10,
        help_text="The shopkeeper will see this. Say what needs to be corrected.",
    )
