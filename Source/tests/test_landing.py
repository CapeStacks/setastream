from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class LandingPageTests(TestCase):
    def test_landing_page_is_the_public_home_page(self):
        response = self.client.get(reverse("landing"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/landing.html")
        self.assertContains(response, "Automate the boring certificate work")
        self.assertContains(response, "Upload an existing design")
        self.assertContains(response, "Create a certificate design")
        self.assertContains(response, "Manual entry")
        self.assertContains(response, "Add recipient data")
        self.assertContains(response, "Generate personalised certificates")
        self.assertContains(response, "recipients.csv")
        self.assertContains(response, "static/images/logo.JPG")
        self.assertContains(response, f'href="{reverse("signup")}">Sign up</a>')
        self.assertNotContains(response, ">Log in</a>")

    def test_actions_handoff_to_login_with_their_destination(self):
        response = self.client.get(reverse("landing"))
        upload_url = response.context["upload_login_url"]
        parsed_login_url = urlparse(upload_url)

        self.assertEqual(parsed_login_url.path, reverse("admin:login"))
        self.assertEqual(
            parse_qs(parsed_login_url.query)["next"],
            [f"{reverse('admin:index')}?intent=upload-template"],
        )

    def test_authenticated_users_skip_the_public_landing_page(self):
        user = User.objects.create_user(
            username="landing-user",
            password="StrongPass!234",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("landing"))

        self.assertRedirects(response, reverse("admin:index"), fetch_redirect_response=False)

    def test_login_returns_user_to_the_selected_action(self):
        password = "StrongPass!234"
        User.objects.create_user(
            username="handoff-user",
            password=password,
            is_staff=True,
        )
        landing_response = self.client.get(reverse("landing"))

        response = self.client.post(
            landing_response.context["create_login_url"],
            {"username": "handoff-user", "password": password},
        )

        self.assertRedirects(
            response,
            f"{reverse('admin:index')}?intent=create-template",
            fetch_redirect_response=False,
        )
