import csv
import os
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import FileResponse, Http404, HttpResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Profile
from accounts.utils import get_profile
from instruments.models import Instrument

from .forms import (
    ApplicationForm, DocumentForm, InspectionForm, PaymentForm, RejectForm, ScheduleForm,
)
from .models import Application, Certificate, Document, Inspection, Notification, Payment
from .pdf import build_certificate_pdf
from .services import issue_certificate, notify, notify_officers

STAFF_ROLES = (Profile.OFFICER, Profile.ADMIN)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _paginate(request, queryset, per_page=8, **params):
    """Return (page_obj, query_string) so filters survive when changing page."""
    page_obj = Paginator(queryset, per_page).get_page(request.GET.get("page"))
    return page_obj, urlencode(params)


def _detail_context(app):
    return {
        "app": app,
        "documents": app.documents.all(),
        "payment": Payment.objects.filter(application=app).first(),
        "inspection": Inspection.objects.filter(application=app).first(),
        "certificate": Certificate.objects.filter(application=app).first(),
        "steps": app.progress(),
    }


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
def home(request):
    return render(request, "home.html", {
        "certificates_issued": Certificate.objects.count(),
        "instruments_registered": Instrument.objects.count(),
    })


def verify_certificate(request, number=None):
    """Public page: anyone can check a certificate number (also opened by the QR code)."""
    number = (number or request.GET.get("number", "")).strip().upper()
    certificate = None
    state = None
    if number:
        certificate = (
            Certificate.objects
            .select_related("application__instrument__category", "application__applicant")
            .filter(number=number)
            .first()
        )
        if certificate is None:
            state = "not_found"
        else:
            state = "valid" if certificate.is_valid else "expired"
    return render(request, "verification/verify.html", {
        "number": number, "certificate": certificate, "state": state,
    })


# ---------------------------------------------------------------------------
# Shopkeeper (owner) pages
# ---------------------------------------------------------------------------
@role_required(Profile.OWNER)
def owner_dashboard(request):
    user = request.user
    applications = Application.objects.filter(applicant=user)
    counts = {row["status"]: row["n"] for row in applications.values("status").annotate(n=Count("id"))}

    instruments = Instrument.objects.filter(owner=user).select_related("category")
    soon = timezone.localdate() + timedelta(days=30)
    renewals = []
    never_verified = 0
    for instrument in instruments:
        certificate = instrument.latest_certificate()
        if certificate is None:
            never_verified += 1
        elif certificate.valid_until <= soon:
            renewals.append((instrument, certificate))

    # Session: instruments opened recently
    recent_ids = request.session.get("recent_instruments", [])
    by_id = {i.pk: i for i in instruments.filter(pk__in=recent_ids)}
    recent = [by_id[pk] for pk in recent_ids if pk in by_id]

    # Cookie: time of the previous visit
    last_visit = None
    raw = request.COOKIES.get("last_visit")
    if raw:
        try:
            last_visit = datetime.fromisoformat(raw)
        except ValueError:
            last_visit = None

    response = render(request, "verification/owner_dashboard.html", {
        "instrument_count": instruments.count(),
        "open_count": sum(counts.get(s, 0) for s in Application.ACTIVE_STATUSES),
        "certified_count": counts.get(Application.CERTIFIED, 0),
        "rejected_count": counts.get(Application.REJECTED, 0),
        "awaiting_payment": applications.filter(status=Application.PENDING_PAYMENT),
        "latest_applications": applications.select_related("instrument")[:5],
        "renewals": renewals,
        "never_verified": never_verified,
        "recent": recent,
        "last_visit": last_visit,
    })
    response.set_cookie(
        "last_visit", timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        max_age=30 * 24 * 3600, samesite="Lax",
    )
    return response


@role_required(Profile.OWNER)
def application_list(request):
    qs = Application.objects.filter(applicant=request.user).select_related("instrument", "instrument__category")
    status = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()
    if status in dict(Application.STATUS_CHOICES):
        qs = qs.filter(status=status)
    else:
        status = ""
    if q:
        qs = qs.filter(
            Q(reference__icontains=q) | Q(instrument__serial_number__icontains=q)
            | Q(instrument__make__icontains=q)
        )
    page_obj, query = _paginate(request, qs, status=status, q=q)
    return render(request, "verification/application_list.html", {
        "page_obj": page_obj, "query": query, "status": status, "q": q,
        "statuses": Application.STATUS_CHOICES,
    })


@role_required(Profile.OWNER)
def apply(request):
    form = ApplicationForm(request.POST or None, request.FILES or None, user=request.user)
    if not form.fields["instrument"].queryset.exists():
        messages.info(
            request,
            "You have no instrument that is free to verify. Register an instrument first.",
        )
        return redirect("instruments:add")
    initial_pk = request.GET.get("instrument", "")
    if initial_pk.isdigit() and request.method != "POST":
        form.initial["instrument"] = int(initial_pk)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            app = Application.objects.create(
                instrument=data["instrument"],
                applicant=request.user,
                fee=data["instrument"].category.verification_fee,
            )
            Document.objects.create(application=app, doc_type=data["doc_type"], file=data["document"])
            if data.get("extra_document"):
                Document.objects.create(
                    application=app, doc_type=data["extra_doc_type"], file=data["extra_document"]
                )
        messages.success(request, "Application saved. Pay the fee to send it to the inspection officers.")
        return redirect("verification:pay", pk=app.pk)
    return render(request, "form_page.html", {
        "form": form,
        "page_title": "Apply for verification",
        "intro": "Pick the instrument and upload a licence or ID proof. You pay the fee on the next step.",
        "submit_label": "Save and continue to payment",
        "multipart": True,
        "cancel_url": "verification:application_list",
    })


@role_required(Profile.OWNER)
def application_detail(request, pk):
    app = get_object_or_404(
        Application.objects.select_related("instrument", "instrument__category", "officer"),
        pk=pk, applicant=request.user,
    )
    return render(request, "verification/application_detail.html", _detail_context(app))


@role_required(Profile.OWNER)
def pay(request, pk):
    """Simulated payment page."""
    app = get_object_or_404(Application.objects.select_related("instrument"), pk=pk, applicant=request.user)
    if app.status != Application.PENDING_PAYMENT:
        messages.info(request, "This application has already been paid for.")
        return redirect("verification:application_detail", pk=app.pk)
    form = PaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            Payment.objects.create(
                application=app, amount=app.fee, method=form.cleaned_data["method"],
                transaction_id="TXN" + uuid.uuid4().hex[:10].upper(),
            )
            app.status = Application.SUBMITTED
            app.save(update_fields=["status", "updated_at"])
        notify_officers(
            f"New application {app.reference} for {app.instrument} is waiting for review.",
            reverse("verification:officer_application_detail", args=[app.pk]),
        )
        messages.success(request, "Payment received. Your application has been submitted.")
        return redirect("verification:application_detail", pk=app.pk)
    return render(request, "verification/payment.html", {"app": app, "form": form})


@role_required(Profile.OWNER)
@require_POST
def resubmit(request, pk):
    app = get_object_or_404(Application, pk=pk, applicant=request.user)
    if app.status != Application.REJECTED:
        messages.error(request, "Only rejected applications can be submitted again.")
        return redirect("verification:application_detail", pk=app.pk)
    app.status = Application.SUBMITTED
    app.officer = None
    app.inspection_date = None
    app.inspection_note = ""
    app.rejection_reason = ""
    app.save()
    notify_officers(
        f"Application {app.reference} was corrected and submitted again.",
        reverse("verification:officer_application_detail", args=[app.pk]),
    )
    messages.success(request, "Application submitted again.")
    return redirect("verification:application_detail", pk=app.pk)


@role_required(Profile.OWNER)
def add_document(request, pk):
    app = get_object_or_404(Application, pk=pk, applicant=request.user)
    if app.status not in (Application.PENDING_PAYMENT, Application.SUBMITTED, Application.REJECTED):
        messages.error(request, "Documents can't be added at this stage.")
        return redirect("verification:application_detail", pk=app.pk)
    form = DocumentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.application = app
        document.save()
        messages.success(request, "Document uploaded.")
        return redirect("verification:application_detail", pk=app.pk)
    return render(request, "form_page.html", {
        "form": form,
        "page_title": f"Add a document to {app.reference}",
        "submit_label": "Upload document",
        "multipart": True,
        "cancel_url": "verification:application_list",
    })


@login_required
def document_download(request, pk):
    """Uploaded files are only visible to the applicant and to officers."""
    document = get_object_or_404(Document.objects.select_related("application"), pk=pk)
    is_owner = document.application.applicant_id == request.user.pk
    if not (is_owner or get_profile(request.user).role in STAFF_ROLES):
        raise PermissionDenied
    try:
        handle = document.file.open("rb")
    except FileNotFoundError:
        raise Http404("The file is missing from the server.")
    return FileResponse(handle, filename=os.path.basename(document.file.name))


@login_required
def certificate_pdf(request, number):
    certificate = get_object_or_404(
        Certificate.objects.select_related(
            "application__instrument__category", "application__applicant", "issued_by"
        ),
        number=number,
    )
    is_owner = certificate.application.applicant_id == request.user.pk
    if not (is_owner or get_profile(request.user).role in STAFF_ROLES):
        raise PermissionDenied
    verify_url = request.build_absolute_uri(reverse("verification:verify_number", args=[certificate.number]))
    pdf_bytes = build_certificate_pdf(certificate, verify_url)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="certificate-{certificate.number}.pdf"'
    return response


# ---------------------------------------------------------------------------
# Notifications (all logged-in users)
# ---------------------------------------------------------------------------
@login_required
def notification_list(request):
    return render(request, "verification/notifications.html", {
        "notifications": Notification.objects.filter(user=request.user)[:50],
    })


@login_required
@require_POST
def notifications_mark_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("verification:notifications")


# ---------------------------------------------------------------------------
# Officer pages
# ---------------------------------------------------------------------------
@role_required(*STAFF_ROLES)
def officer_dashboard(request):
    apps = Application.objects.exclude(status=Application.PENDING_PAYMENT)
    counts = {row["status"]: row["n"] for row in apps.values("status").annotate(n=Count("id"))}
    return render(request, "verification/officer_dashboard.html", {
        "waiting": apps.filter(status=Application.SUBMITTED).select_related("instrument", "applicant")[:8],
        "mine": apps.filter(officer=request.user).exclude(
            status__in=[Application.CERTIFIED, Application.REJECTED]
        ).select_related("instrument")[:8],
        "submitted_count": counts.get(Application.SUBMITTED, 0),
        "in_progress_count": sum(
            counts.get(s, 0)
            for s in (Application.UNDER_REVIEW, Application.SCHEDULED, Application.INSPECTED)
        ),
        "certified_count": counts.get(Application.CERTIFIED, 0),
        "rejected_count": counts.get(Application.REJECTED, 0),
    })


@role_required(*STAFF_ROLES)
def officer_applications(request):
    qs = (
        Application.objects.exclude(status=Application.PENDING_PAYMENT)
        .select_related("instrument", "instrument__category", "applicant", "applicant__profile")
    )
    status = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()
    if status in dict(Application.STATUS_CHOICES):
        qs = qs.filter(status=status)
    else:
        status = ""
    if q:
        qs = qs.filter(
            Q(reference__icontains=q) | Q(instrument__serial_number__icontains=q)
            | Q(applicant__username__icontains=q) | Q(applicant__profile__shop_name__icontains=q)
        )
    page_obj, query = _paginate(request, qs, status=status, q=q)
    return render(request, "verification/officer_applications.html", {
        "page_obj": page_obj, "query": query, "status": status, "q": q,
        "statuses": [s for s in Application.STATUS_CHOICES if s[0] != Application.PENDING_PAYMENT],
    })


@role_required(*STAFF_ROLES)
def officer_application_detail(request, pk):
    app = get_object_or_404(
        Application.objects.select_related(
            "instrument", "instrument__category", "applicant", "applicant__profile", "officer"
        ),
        pk=pk,
    )
    if app.status == Application.PENDING_PAYMENT:
        raise Http404
    context = _detail_context(app)
    role = get_profile(request.user).role
    context["can_act"] = role == Profile.ADMIN or app.officer_id in (None, request.user.pk)
    return render(request, "verification/officer_application_detail.html", context)


def _application_for_action(request, pk, allowed_statuses):
    """Load an application for an officer action, or return (None, redirect_response)."""
    app = get_object_or_404(
        Application.objects.select_related("instrument", "instrument__category", "applicant"), pk=pk
    )
    if app.status == Application.PENDING_PAYMENT:
        raise Http404
    role = get_profile(request.user).role
    if role != Profile.ADMIN and app.officer_id not in (None, request.user.pk):
        raise PermissionDenied
    if app.status not in allowed_statuses:
        messages.error(request, "This step isn't available at the application's current stage.")
        return None, redirect("verification:officer_application_detail", pk=app.pk)
    return app, None


def _owner_url(app):
    return reverse("verification:application_detail", args=[app.pk])


@role_required(*STAFF_ROLES)
@require_POST
def officer_start_review(request, pk):
    app, early = _application_for_action(request, pk, [Application.SUBMITTED])
    if early:
        return early
    app.status = Application.UNDER_REVIEW
    app.officer = request.user
    app.save(update_fields=["status", "officer", "updated_at"])
    notify(app.applicant, f"Application {app.reference} is now under review.", _owner_url(app))
    messages.success(request, "You are now reviewing this application.")
    return redirect("verification:officer_application_detail", pk=app.pk)


@role_required(*STAFF_ROLES)
def officer_schedule(request, pk):
    app, early = _application_for_action(request, pk, [Application.UNDER_REVIEW, Application.SCHEDULED])
    if early:
        return early
    form = ScheduleForm(
        request.POST or None,
        initial={"inspection_date": app.inspection_date, "note": app.inspection_note},
    )
    if request.method == "POST" and form.is_valid():
        app.inspection_date = form.cleaned_data["inspection_date"]
        app.inspection_note = form.cleaned_data["note"]
        app.status = Application.SCHEDULED
        if app.officer_id is None:
            app.officer = request.user
        app.save(update_fields=["inspection_date", "inspection_note", "status", "officer", "updated_at"])
        notify(
            app.applicant,
            f"Inspection for {app.reference} is scheduled on {app.inspection_date:%d %b %Y}.",
            _owner_url(app),
        )
        messages.success(request, "Inspection scheduled and the shopkeeper has been notified.")
        return redirect("verification:officer_application_detail", pk=app.pk)
    return render(request, "form_page.html", {
        "form": form,
        "page_title": f"Schedule inspection for {app.reference}",
        "intro": f"{app.instrument} owned by {app.applicant.username}.",
        "submit_label": "Schedule inspection",
        "cancel_url_pk": ("verification:officer_application_detail", app.pk),
    })


@role_required(*STAFF_ROLES)
def officer_inspect(request, pk):
    app, early = _application_for_action(request, pk, [Application.SCHEDULED, Application.INSPECTED])
    if early:
        return early
    existing = Inspection.objects.filter(application=app).first()
    form = InspectionForm(request.POST or None, instance=existing)
    if request.method == "POST" and form.is_valid():
        inspection = form.save(commit=False)
        inspection.application = app
        inspection.officer = request.user
        inspection.save()
        app.status = Application.INSPECTED
        app.save(update_fields=["status", "updated_at"])
        messages.success(request, "Inspection results saved.")
        return redirect("verification:officer_application_detail", pk=app.pk)
    return render(request, "form_page.html", {
        "form": form,
        "page_title": f"Inspection results for {app.reference}",
        "intro": (
            f"{app.instrument}, capacity {app.instrument.capacity.normalize():f} {app.instrument.unit}. "
            "The instrument passes when the difference between the observed and reference value "
            "is within the permissible error."
        ),
        "submit_label": "Save results",
        "cancel_url_pk": ("verification:officer_application_detail", app.pk),
    })


@role_required(*STAFF_ROLES)
@require_POST
def officer_approve(request, pk):
    app, early = _application_for_action(request, pk, [Application.INSPECTED])
    if early:
        return early
    inspection = Inspection.objects.filter(application=app).first()
    if inspection is None or not inspection.within_tolerance:
        messages.error(request, "The readings are outside the permissible error. Reject the application instead.")
        return redirect("verification:officer_application_detail", pk=app.pk)
    certificate = issue_certificate(app, request.user)
    messages.success(request, f"Certificate {certificate.number} issued.")
    return redirect("verification:officer_application_detail", pk=app.pk)


@role_required(*STAFF_ROLES)
def officer_reject(request, pk):
    app, early = _application_for_action(
        request, pk,
        [Application.SUBMITTED, Application.UNDER_REVIEW, Application.SCHEDULED, Application.INSPECTED],
    )
    if early:
        return early
    form = RejectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        app.status = Application.REJECTED
        app.rejection_reason = form.cleaned_data["reason"]
        if app.officer_id is None:
            app.officer = request.user
        app.save(update_fields=["status", "rejection_reason", "officer", "updated_at"])
        notify(app.applicant, f"Application {app.reference} was rejected. Open it to see why.", _owner_url(app))
        messages.success(request, "Application rejected. The shopkeeper can correct it and submit again.")
        return redirect("verification:officer_application_detail", pk=app.pk)
    return render(request, "form_page.html", {
        "form": form,
        "page_title": f"Reject {app.reference}",
        "submit_label": "Reject application",
        "cancel_url_pk": ("verification:officer_application_detail", app.pk),
    })


# ---------------------------------------------------------------------------
# Administrator pages
# ---------------------------------------------------------------------------
@role_required(Profile.ADMIN)
def admin_dashboard(request):
    today = timezone.localdate()
    counts = {row["status"]: row["n"] for row in Application.objects.values("status").annotate(n=Count("id"))}
    return render(request, "verification/admin_dashboard.html", {
        "owner_count": Profile.objects.filter(role=Profile.OWNER).count(),
        "officer_count": Profile.objects.filter(role=Profile.OFFICER).count(),
        "instrument_count": Instrument.objects.count(),
        "status_rows": [(label, counts.get(key, 0), key) for key, label in Application.STATUS_CHOICES],
        "revenue": Payment.objects.aggregate(total=Sum("amount"))["total"] or 0,
        "valid_certificates": Certificate.objects.filter(valid_until__gte=today).count(),
        "expired_certificates": Certificate.objects.filter(valid_until__lt=today).count(),
        "expiring_certificates": Certificate.objects.filter(
            valid_until__gte=today, valid_until__lte=today + timedelta(days=30)
        ).count(),
    })


@role_required(Profile.ADMIN)
def reports(request):
    labels = dict(Application.STATUS_CHOICES)
    by_status = [
        (labels[row["status"]], row["n"])
        for row in Application.objects.values("status").annotate(n=Count("id")).order_by("status")
    ]
    by_category = [
        (row["instrument__category__name"], row["n"])
        for row in Application.objects.values("instrument__category__name")
        .annotate(n=Count("id")).order_by("-n")
    ]
    monthly = [
        (row["month"].strftime("%B %Y"), row["n"])
        for row in Certificate.objects.annotate(month=TruncMonth("issued_on"))
        .values("month").annotate(n=Count("id")).order_by("month")
    ]
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="verification-report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Report", "Item", "Count"])
        for item, n in by_status:
            writer.writerow(["Applications by status", item, n])
        for item, n in by_category:
            writer.writerow(["Applications by category", item, n])
        for item, n in monthly:
            writer.writerow(["Certificates issued by month", item, n])
        return response
    return render(request, "verification/reports.html", {
        "by_status": by_status, "by_category": by_category, "monthly": monthly,
    })


# ---------------------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------------------
def error_403(request, exception=None):
    return render(request, "403.html", status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    # Rendered without a request so it works even when context processors fail.
    return HttpResponseServerError(render_to_string("500.html"))
