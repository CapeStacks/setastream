from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class SignUpTests(TestCase):
    def signup_data(self, **overrides):
        data = {
            "first_name": "Amina",
            "last_name": "Dlamini",
            "email": "amina@example.com",
            "password1": "StrongPass!234",
            "password2": "StrongPass!234",
        }
        data.update(overrides)
        return data

    def test_signup_page_renders(self):
        response = self.client.get(reverse("signup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create account")
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password1"')

    def test_signup_creates_inactive_non_staff_user(self):
        response = self.client.post(reverse("signup"), self.signup_data())

        self.assertRedirects(response, f'{reverse("signup")}?submitted=1')
        user = User.objects.get(username="amina@example.com")
        self.assertEqual(user.email, "amina@example.com")
        self.assertEqual(user.first_name, "Amina")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password("StrongPass!234"))

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username="existing-user",
            email="amina@example.com",
            password="StrongPass!234",
        )

        response = self.client.post(reverse("signup"), self.signup_data())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account request already exists")
        self.assertEqual(User.objects.count(), 1)

    def test_login_page_links_to_signup(self):
        response = self.client.get(reverse("admin:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("signup")}"')
