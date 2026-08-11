from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import SignUpForm


def signup(request):
    registration_complete = request.GET.get("submitted") == "1"

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
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
