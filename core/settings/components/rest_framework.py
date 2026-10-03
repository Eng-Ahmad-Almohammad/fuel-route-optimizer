"""Django Rest Framework settings file for the core django project."""

REST_FRAMEWORK = {
    # The trip API is public and stateless: no login, no sessions, no CSRF.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}
