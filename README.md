# Fuel Route Optimizer

## Description

A Django REST API that plans a driving route between two locations in the USA and returns the most cost-effective fuel stops along the way.

- Returns the route map along with the optimal places to fuel up, picked mainly by fuel price.
- Assumes a maximum vehicle range of 500 miles, so long routes can include more than one stop.
- Returns the total fuel cost, assuming the vehicle gets 10 miles per gallon.
- Makes as few calls as possible to the external routing API (ideally one per request) to keep responses fast.

Built with Django 6.1 and Django REST Framework.

## Setup and Run the Project Locally

### 1. Clone the Repository

First, clone the repository to your local machine:

```bash
git clone <repository-url>
cd fuel-route-optimizer
```

### 2. Generate Virtual Environment

Create a virtual environment to ensure consistency in dependencies.

```bash
python -m venv .venv
```

Activate the virtual environment:

```bash
# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Required Packages

```bash
# development (includes linters, type checking and test tools)
pip install -r requirements/development.txt

# runtime only
pip install -r requirements/base.txt
```

### 4. Environment variables

create `.env` file on the root of the project and copy the variables from `.env.template` file and replace the values with your values.

### 5. Run Migrations

Apply the database migrations to set up the initial schema for the database:

```bash
python manage.py migrate
```

### 6. Load the Fuel Stations

Load the US places and the truck stop fuel prices from `data/` into the database (takes a couple of seconds, see
`data/README.md`):

```bash
python manage.py load_fuel_data
```

### 7. Add the Routing API Key

Create a free account at [openrouteservice.org](https://openrouteservice.org/dev/#/signup) and set
`OPENROUTESERVICE_API_KEY` in `.env`.

### 8. Run the Server

Start the development server to test the application locally:

```bash
python manage.py runserver
```

By default, the application will run using an SQLite database.

## Using the API

`start` and `finish` are US places written as `City, ST`. Send them as JSON (POST) or as query parameters (GET):

```bash
curl -X POST http://localhost:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start": "New York, NY", "finish": "Los Angeles, CA"}'

curl "http://localhost:8000/api/route/?start=Chicago,%20IL&finish=Houston,%20TX"
```

The response has the total distance, gallons and fuel cost, the fuel stops in driving order (station, mile marker,
price, gallons, cost), the planning assumptions, and the route as a GeoJSON `FeatureCollection` (paste it into
[geojson.io](https://geojson.io) to view it). `map_url` opens the same trip on a map at `/map/`.

| Status | When |
| --- | --- |
| 200 | Trip planned. `cached: true` means it was served without calling the routing API. |
| 400 | `start`/`finish` missing, not in `City, ST` form, unknown, or the same place. |
| 422 | No drivable route, or a stretch longer than 500 miles without a fuel station. |
| 502 | The routing service failed (network error, invalid API key, rate limit). |

### How a trip is planned

1. Both places are looked up in the `Place` table (no geocoding API).
2. **One** call to [OpenRouteService](https://openrouteservice.org) returns the road as a line of points plus its
   length. Results are cached per start/finish pair for 6 hours.
3. Stations within 10 miles of the road are found with a bounding-box query and a grid index, and each gets the mile
   marker of the nearest route point.
4. A dynamic program picks the stops that minimize fuel cost plus $5 per stop, so the plan doesn't stop for a gallon
   to save a few cents (see `routing/optimizer.py`). The tank holds 500 miles of fuel at 10 mpg and starts empty; the
   first stop is a station within 25 miles of the start.

### Known limitations

- **Places are town centers.** Start, finish and every fuel station are placed at the center of their town (US Census
  Gazetteer), because the price list only gives highway-exit addresses. Stations can be a few miles from their true
  spot; the 10-mile corridor allows for that, but the small detour to reach a station is not counted.
- **Input is "City, ST" only.** Street addresses and places outside the US are rejected with a 400.
- **Road snapping is limited to 350 m.** The free OpenRouteService API snaps start and finish to a road only within
  350 m. A small town whose center is farther than that from any road returns a 422 ("Could not find routable
  point"). All trips tried so far worked; a fix would be to store a road-snapped point for such towns offline.
- **The cheapest plan counts each stop as $5.** This is a planning weight, not money spent: it avoids stopping for a
  gallon to save a few cents. Set `STOP_COST_DOLLARS = 0` in `routing/planner.py` for the strictly cheapest fuel bill.

## Workflow

**Note: Ensure to run `pre-commit install` command before doing your first commit.**

The project follows a Gitflow workflow for version control and collaboration. Key aspects of the workflow include:

- Feature Branches: Each new feature should be developed in a dedicated branch named `feature/{Clickup-task-id}`

- Main Branch: The `main` branch holds the stable, production-ready code.

- Development Branch: The `dev` branch serves as an integration branch for feature branches. Regular updates from `dev` are merged into `main` when a new release is ready.

- Pull Requests: All changes should go through a pull request for code review before merging into the `dev` branch.

## Naming Syntax

### Branch Naming

- Feature Branches: `feature/{Clickup-task-id}`

- Bugfix Branches: `bugfix/{Clickup-task-id}`

- Hotfix Branches: `hotfix/issue-description` (e.g., `hotfix/critical-database-fix`)

### File Naming

- Python Files: Use lowercase letters with underscores (e.g., `license_management.py`).

- Templates: Use lowercase letters with hyphens (e.g., `user-profile.html`).

- Static Files: Organize by type (e.g., css, js, images) and use lowercase letters with hyphens.

- URL: Use lowercase letters with hyphens and it must end with forward slash (e.g., `/manage-users/`).

## Commit Message Format

Use a consistent commit message structure:

Format: `[TYPE] [SCOPE]: [SUMMARY]`

### Types

- feat: For new features (e.g., `feat(module): add health certification module`)

- fix: For bug fixes (e.g., `fix(database): resolve database connection issue`)

- docs: For documentation updates (e.g., `docs(README): update README file`)

- style: For code style improvements (e.g., `style(flake8): format code according to PEP8`)

- refactor: For refactoring code (e.g., `refactor(users): improve data handling logic`)

- test: For adding or modifying tests (e.g., `test(license): add unit tests for license module`)

- chore: For maintenance and other tasks (e.g., `chore(dependencies): update dependencies`)

### Commit template (On the remote git host)

```markdown
# Commit Message Template

[TYPE] [SCOPE]: [SUMMARY]

# Description

[Provide a brief explanation of the change. Include what was done, why it was done, and any relevant context.]

# Ticket URL

[TICKET_URL]

# Changes Made

- [List the key changes made in the codebase, bullet-point style.]

# Checklist

- [ ] Code is properly formatted.
- [ ] Tests have been added or updated (if applicable).
- [ ] Documentation has been updated (if applicable).
- [ ] No breaking changes introduced.

# Examples

# A commit with this template might look like:

feat(auth): add JWT-based authentication

# Description

Added support for JWT-based authentication to improve security and support stateless authentication.

# Ticket URL

https://example.com/tickets/123

# Changes Made

- Added a `login` endpoint to generate JWTs.
- Created middleware to validate JWTs on protected routes.
- Updated user model to include refresh token support.

# Testing

- Verified successful login with valid credentials.
- Tested token validation for expired and malformed tokens.
- Updated existing unit tests and added new ones for authentication flows.

# Checklist

- [x] Code is properly formatted.
- [x] Tests have been added or updated.
- [x] Documentation has been updated.
- [ ] No breaking changes introduced.
```

## Tools used

| Package Name                     | Usage                                                                                                                                                                                                                                                                                                                                                                                                                       | Installation                              |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Django                           | Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design. Built by experienced developers, it takes care of much of the hassle of web development, so you can focus on writing your app without needing to reinvent the wheel. It’s free and open source.                                                                                                                  | pip install django                        |
| Django Rest Framework            | Django REST framework is a powerful and flexible toolkit for building Web APIs.                                                                                                                                                                                                                                                                                                                                             | pip install djangorestframework           |
| Django Environ                   | Python package that allows you to use Twelve-factor methodology to configure your Django application with environment variables.                                                                                                                                                                                                                                                                                            | pip install django-environ                |
| Django Split Settings            | Organize Django settings into multiple files and directories. Easily override and modify settings. Use wildcards in settings file paths and mark settings files as optional.                                                                                                                                                                                                                                                | pip install django-split-settings         |
| Gunicorn                         | Gunicorn `Green Unicorn` is a Python WSGI HTTP Server for UNIX. It’s a pre-fork worker model ported from Ruby’s Unicorn project. The Gunicorn server is broadly compatible with various web frameworks, simply implemented, light on server resources, and fairly speedy.                                                                                                                                                   | pip install gunicorn                      |
| Requests                         | HTTP client used to call the routing API and, for one-off data preparation, the Nominatim geocoder.                                                                                                                                                                                                                                                                                                                         | pip install requests                      |
| Django Cors Headers              | A Django App that adds Cross-Origin Resource Sharing (CORS) headers to responses. This allows in-browser requests to your Django application from other origins.                                                                                                                                                                                                                                                            | pip install django-cors-headers           |
| Flake8                           | Command-line utility for enforcing style consistency across Python projects                                                                                                                                                                                                                                                                                                                                                 | pip install flake8                        |
| Flake8 DocStrings                | A simple module that adds an extension for the fantastic `pydocstyle` tool to flake8.                                                                                                                                                                                                                                                                                                                                       | pip install flake8-docstrings             |
| Flake8 BugBear                   | A plugin for Flake8 finding likely bugs and design problems in your program.                                                                                                                                                                                                                                                                                                                                                | pip install flake8-bugbear                |
| Flake8 Annotations               | A plugin that detects the absence of PEP 3107-style function annotations.                                                                                                                                                                                                                                                                                                                                                   | pip install flake8-annotations            |
| Flake8 Commas                    | Extension for enforcing trailing commas.                                                                                                                                                                                                                                                                                                                                                                                    | pip install flake8-commas                 |
| Flake8 Sort                      | To check if the imports on your python files are sorted the way you expect.                                                                                                                                                                                                                                                                                                                                                 | pip install flake8-isort                  |
| Flake8 Simplify                  | A flake8 plugin designed to identify and suggest simpler alternatives for common code patterns in Python.                                                                                                                                                                                                                                                                                                                   | pip install flake8_simplify               |
| Flake8 Pytest Style              | A plugin checking common style issues or inconsistencies with pytest-based tests.                                                                                                                                                                                                                                                                                                                                           | pip install flake8 Pytest Style           |
| Flake8 Comprehensions            | A plugin that helps you write better list/set/dict comprehensions.                                                                                                                                                                                                                                                                                                                                                          | pip install flake8-comprehensions         |
| Flake8 Debugger                  | A plugin that helps developers catch and remove debugger statements, like pdb and ipdb, in Python code.                                                                                                                                                                                                                                                                                                                     | pip install flake8-debugger               |
| Flake8 Eradicate                 | A plugin to find commented out (or so called "dead") code.                                                                                                                                                                                                                                                                                                                                                                  | pip install flake8-eradicate              |
| Flake8 rst docstrings            | A flake8 plugin that checks Python docstrings formatted in reStructuredText (reST) for syntax correctness.                                                                                                                                                                                                                                                                                                                  | pip install flake8-rst-docstrings         |
| Flake8 Quotes                    | A plugin that enforces consistency in the use of quote marks for strings in Python code.                                                                                                                                                                                                                                                                                                                                    | pip install flake8-quotes                 |
| Black                            | A Python code formatter that automatically formats Python code to comply with its style guide called PEP 8.                                                                                                                                                                                                                                                                                                                 | pip install black                         |
| Isort                            | A Python utility that helps in sorting and organizing import statements in Python code to create readable and consistent code.                                                                                                                                                                                                                                                                                              | pip install isort                         |
| Django-stubs                     | A type-checking plugin for Django that provides type annotations for Django's built-in classes, models, and other components.                                                                                                                                                                                                                                                                                               | pip install django-stubs                  |
| Coverage                         | A tool that measures code coverage, helping developers understand which parts of the code are executed during tests and identify untested areas.                                                                                                                                                                                                                                                                            | pip install coverage                      |
| Django Debug Toolbar             | configurable set of panels that display debug information for Django during development, useful for profiling and optimizing your application.                                                                                                                                                                                                                                                                              | pip install django-debug-toolbar          |
| Pytest                           | A powerful testing framework for Python that simplifies writing tests with features like fixtures, parameterization, and assert rewriting.                                                                                                                                                                                                                                                                                  | pip install pytest                        |
| Pytest Cov                       | A pytest plugin for measuring code coverage using Coverage and integrating the results with pytest’s test reports.                                                                                                                                                                                                                                                                                                          | pip install pytest-cov                    |
| Pytest Django                    | A pytest plugin that provides tools for testing Django applications, including database fixtures and environment setup.                                                                                                                                                                                                                                                                                                     | pip install pytest-django                 |
| Pytest Mock                      | A pytest plugin that integrates Python’s `unittest.mock` module, simplifying mocking and patching in tests.                                                                                                                                                                                                                                                                                                                 | pip install pytest-mock                   |
