"""Settings for the test suite.

Loads the regular settings with the `testing` environment, then swaps in an in-memory database and
placeholder secrets so the tests run without a `.env` file and never reach the real routing API.
"""

import os

os.environ.setdefault("DJANGO_ENV", "testing")

from core.settings import *  # noqa: E402, F401, F403

SECRET_KEY = "test-secret-key"  # noqa: S105
OPENROUTESERVICE_API_KEY = "test-openrouteservice-key"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
