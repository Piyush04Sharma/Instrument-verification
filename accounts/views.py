from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import ProfileForm, RegistrationForm
from .models import Profile
from .utils import get_profile


class SiteLoginView(LoginView):
    """Login page. Uses the shared form template."""

    template_name = "form_page.html"
    redirect_authenticated_user = True
    extra_context = {
        "page_title": "Log in",
        "intro": "Use the username and password you registered with.",
        "submit_label": "Log in",
        "alt_text": "New shopkeeper?",
        "alt_label": "Create an account",
        "alt_url": reverse_lazy("accounts:register"),
    }


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)  # session is created here
        messages.success(request, "Your account is ready. Register your first instrument.")
        return redirect("accounts:dashboard")
    return render(request, "form_page.html", {
        "form": form,
        "page_title": "Create a shopkeeper account",
        "intro": "Register once, then add your instruments and apply for verification online.",
        "submit_label": "Create account",
        "alt_text": "Already registered?",
        "alt_label": "Log in",
        "alt_url": reverse_lazy("accounts:login"),
    })


@login_required
def dashboard(request):
    """Send each user to the dashboard that matches their role."""
    role = get_profile(request.user).role
    if role == Profile.OFFICER:
        return redirect("verification:officer_dashboard")
    if role == Profile.ADMIN:
        return redirect("verification:admin_dashboard")
    return redirect("verification:owner_dashboard")


@login_required
def profile(request):
    profile_obj = get_profile(request.user)
    form = ProfileForm(request.POST or None, instance=profile_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "form_page.html", {
        "form": form,
        "page_title": "Your profile",
        "intro": f"Signed in as {request.user.username} ({profile_obj.get_role_display()}).",
        "submit_label": "Save profile",
    })
