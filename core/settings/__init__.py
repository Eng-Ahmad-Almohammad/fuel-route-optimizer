"""
This is a django-split-settings main file.
For more information read this:
https://github.com/sobolevn/django-split-settings
Default environment is `development`.
To change settings file:
`DJANGO_ENV=production python manage.py runserver`
"""

import os
from pathlib import Path

import environ
from split_settings.tools import include

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Data files used to build the station and place tables, see `data/README.md`.
# Custom settings live here, not in the `include()`d files, so the django-stubs mypy plugin can see them.
DATA_DIR = BASE_DIR / "data"

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
env = environ.Env(
    DJANGO_ENV=(str, "development"),
    OPENROUTESERVICE_API_KEY=(str, ""),
    OPENROUTESERVICE_PROFILE=(str, "driving-car"),
)


ENV = env("DJANGO_ENV")

# Routing API (https://openrouteservice.org), called once per uncached trip request.
OPENROUTESERVICE_API_KEY = env("OPENROUTESERVICE_API_KEY")
OPENROUTESERVICE_PROFILE = env("OPENROUTESERVICE_PROFILE")
OPENROUTESERVICE_TIMEOUT_SECONDS = 20
# Trip plans are cached per start/finish pair so repeated requests don't call the routing API again.
TRIP_CACHE_SECONDS = 6 * 60 * 60

base_settings = [
    "common.py",
    "components/*.py",  # standard django settings
    # Select the right env:
    "environments/{0}.py".format(ENV),
]

# Include settings:
include(*base_settings)
