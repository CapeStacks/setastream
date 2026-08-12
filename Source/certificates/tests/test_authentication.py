from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase


User = get_user_model()


class EmailOrUsernameAuthenticationTests(TestCase):
    password = "StrongPass!234"

    def test_authenticates_with_username(self):
        user = User.objects.create_user(
            username="amina",
            email="amina@example.com",
            password=self.password,
        )

        authenticated_user = authenticate(username="amina", password=self.password)

        self.assertEqual(authenticated_user, user)

    def test_authenticates_with_email_case_insensitively(self):
        user = User.objects.create_user(
            username="amina",
            email="Amina@example.com",
            password=self.password,
        )

        authenticated_user = authenticate(
            username="amina@EXAMPLE.com",
            password=self.password,
        )

        self.assertEqual(authenticated_user, user)

    def test_duplicate_email_fails_closed(self):
        User.objects.create_user(
            username="amina",
            email="shared@example.com",
            password=self.password,
        )
        User.objects.create_user(
            username="thabo",
            email="shared@example.com",
            password=self.password,
        )

        authenticated_user = authenticate(
            username="shared@example.com",
            password=self.password,
        )

        self.assertIsNone(authenticated_user)

    def test_username_takes_precedence_over_another_users_email(self):
        username_owner = User.objects.create_user(
            username="shared@example.com",
            email="owner@example.com",
            password=self.password,
        )
        User.objects.create_user(
            username="legacy-user",
            email="shared@example.com",
            password="DifferentPass!234",
        )

        authenticated_user = authenticate(
            username="shared@example.com",
            password=self.password,
        )

        self.assertEqual(authenticated_user, username_owner)
