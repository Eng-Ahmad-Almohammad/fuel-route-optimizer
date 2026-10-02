"""Testing database configurations.

At this module you will add the test database config to septate them
from other configurations.
"""

from core.settings.common import *  # noqa: F403 F401 WPS347
from core.settings.components.rest_framework import *  # noqa: F403 F401 WPS347

DEBUG = True
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # Use an in-memory database for testing
    },
}
