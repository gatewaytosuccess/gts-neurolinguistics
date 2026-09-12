## Prerequisites

- Python 3.13
- PostgreSQL 18+
- A Clerk application (for anything beyond the health check)

## Dev setup

All backend commands run from `api/`.

### 1. Virtualenv

```bash
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Environment

```bash
cp .env.example .env
```

Fill in `.env`. At minimum you need `DJANGO_SECRET_KEY` and `DATABASE_URL`;
the Clerk and AWS values are needed once you touch authenticated endpoints or
media. Generate a dev secret key with:

```bash
.venv/bin/python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

### 3. Database

PostgreSQL must be running and the database created before migrating:

```bash
sudo service postgresql start           # WSL: no systemd
sudo -u postgres createuser -s "$USER"  # once, if your role doesn't exist
createdb gts_neuro
```

Point `DATABASE_URL` at it, then:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
```

### 4. Run

```bash
.venv/bin/python manage.py runserver    # http://127.0.0.1:8000
```

- `GET /api/health/` — liveness plus a database connection check
- `/admin/` — Django admin (superuser password login, unrelated to Clerk)

Settings default to `config.settings.dev`; production sets
`DJANGO_SETTINGS_MODULE=config.settings.prod`.

## Frontend

`web/` is empty — the Next.js app hasn't been scaffolded yet. When it is, it
runs on http://localhost:3000, which is what the CORS, CSRF, and Clerk
authorized-party settings in `api/.env.example` already expect.

## Repo layout

```
api/            Django project (config, common, users, courses,
                enrollments, commerce, reviews)
web/            Next.js app (TBD)
SPEC.md         feature spec, grouped by page
SCHEMA.md       database schema
DESIGN.md       frontend design
```
