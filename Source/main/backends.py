from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticate against both email and username.

    Usernames are unique and take precedence. Email authentication fails closed
    when legacy data contains duplicate email addresses, rather than choosing an
    arbitrary account or raising ``MultipleObjectsReturned``.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("email")

        if username is None or password is None:
            return None

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            email_matches = list(
                User.objects.filter(email__iexact=username).order_by("pk")[:2]
            )
            if len(email_matches) != 1:
                # Run the default password hasher once to reduce timing attacks.
                User().set_password(password)
                return None
            user = email_matches[0]

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        if not user.has_usable_password():
            # Keep the work done for unusable passwords comparable to a miss.
            User().set_password(password)
        return None
