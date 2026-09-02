from urllib.parse import urlencode

from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import SignUpForm


def landing(request):
    """Show the public product page and preserve each action through login."""
    if request.user.is_authenticated:
        return redirect("admin:index")

    admin_url = reverse("admin:index")
    login_url = reverse("admin:login")

    def login_handoff(intent):
        destination = f"{admin_url}?{urlencode({'intent': intent})}"
        return f"{login_url}?{urlencode({'next': destination})}"

    return render(
        request,
        "admin/landing.html",
        {
            "login_url": login_handoff("dashboard"),
            "signup_login_url": login_handoff("signup"),
            "upload_login_url": login_handoff("upload-template"),
            "create_login_url": login_handoff("create-template"),
            "demo_login_url": login_handoff("request-demo"),
            "how_it_works_login_url": login_handoff("how-it-works"),
        },
    )


def signup(request):
    registration_complete = request.GET.get("submitted") == "1"

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except IntegrityError:
                form.add_error("email", form.duplicate_email_error)
            else:
                return redirect(f"{reverse('signup')}?submitted=1")
    else:
        form = SignUpForm()

    return render(
        request,
        "registration/signup.html",
        {
            "form": form,
            "registration_complete": registration_complete,
        },
    )
