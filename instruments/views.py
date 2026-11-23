from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Profile

from .forms import InstrumentForm
from .models import Category, Instrument


@role_required(Profile.OWNER)
def instrument_list(request):
    qs = Instrument.objects.filter(owner=request.user).select_related("category")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    if q:
        qs = qs.filter(
            Q(make__icontains=q) | Q(model_number__icontains=q) | Q(serial_number__icontains=q)
        )
    if category.isdigit():
        qs = qs.filter(category_id=category)
    page_obj = Paginator(qs, 8).get_page(request.GET.get("page"))
    return render(request, "instruments/list.html", {
        "page_obj": page_obj,
        "q": q,
        "category": category,
        "categories": Category.objects.all(),
        "query": urlencode({"q": q, "category": category}),
    })


@role_required(Profile.OWNER)
def instrument_add(request):
    form = InstrumentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        instrument = form.save(commit=False)
        instrument.owner = request.user
        instrument.save()
        messages.success(request, "Instrument registered. You can now apply for verification.")
        return redirect("instruments:detail", pk=instrument.pk)
    return render(request, "form_page.html", {
        "form": form,
        "page_title": "Register an instrument",
        "intro": "Enter the details exactly as printed on the instrument's plate.",
        "submit_label": "Save instrument",
        "cancel_url": "instruments:list",
    })


@role_required(Profile.OWNER)
def instrument_detail(request, pk):
    instrument = get_object_or_404(
        Instrument.objects.select_related("category"), pk=pk, owner=request.user
    )
    # Session: remember the last few instruments this user opened.
    recent = request.session.get("recent_instruments", [])
    if instrument.pk in recent:
        recent.remove(instrument.pk)
    recent.insert(0, instrument.pk)
    request.session["recent_instruments"] = recent[:5]

    return render(request, "instruments/detail.html", {
        "instrument": instrument,
        "applications": instrument.applications.order_by("-created_at"),
        "certificate": instrument.latest_certificate(),
    })


@role_required(Profile.OWNER)
def instrument_edit(request, pk):
    instrument = get_object_or_404(Instrument, pk=pk, owner=request.user)
    if instrument.is_locked:
        messages.error(request, "This instrument already has verification applications and can't be edited.")
        return redirect("instruments:detail", pk=pk)
    form = InstrumentForm(request.POST or None, instance=instrument)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Instrument updated.")
        return redirect("instruments:detail", pk=pk)
    return render(request, "form_page.html", {
        "form": form,
        "page_title": "Edit instrument",
        "submit_label": "Save changes",
        "cancel_url": "instruments:list",
    })


@role_required(Profile.OWNER)
@require_POST
def instrument_delete(request, pk):
    instrument = get_object_or_404(Instrument, pk=pk, owner=request.user)
    if instrument.is_locked:
        messages.error(request, "This instrument has verification applications and can't be deleted.")
        return redirect("instruments:detail", pk=pk)
    instrument.delete()
    messages.success(request, "Instrument deleted.")
    return redirect("instruments:list")
