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
env = environ.Env(DJANGO_ENV=(str, "development"))


ENV = env("DJANGO_ENV")

base_settings = [
    "common.py",
    "components/*.py",  # standard django settings
    # Select the right env:
    "environments/{0}.py".format(ENV),
]

# Include settings:
include(*base_settings)
