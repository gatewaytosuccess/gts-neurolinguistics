# API (Django)

JSON API for the neurolinguistics course platform. The Next.js app in `../web`
is the only client; Django serves no templates apart from the admin.

## Stack

- Django 5.2 + Django REST Framework
- PostgreSQL (local for dev, Amazon RDS in production)
- Clerk for authentication — Django verifies Clerk session JWTs, it does not
  own passwords
- Amazon S3 for lesson media

## Layout

```
api/
  config/            project config
    settings/
      base.py        shared settings, read from the environment
      dev.py         local development (DEBUG, browsable API, console email)
      prod.py        RDS + TLS + security headers
    urls.py          / admin/ and /api/
  common/            UUID + timestamp base models, /api/health/
  users/             custom User model, Clerk JWT authentication
  courses/           Course -> Module -> Lesson
  enrollments/       Enrollment, LessonProgress
  commerce/          Cart, CartItem, Order, OrderItem, Coupon
  reviews/           Review
  .venv/             virtualenv (gitignored)
  .env               local secrets (gitignored) — see .env.example
```

Models follow `../SCHEMA.md`. No serializers, views or routes exist yet beyond
the health check.

## Setup

The virtualenv already exists at `api/.venv`. To recreate it:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the Clerk and AWS values. A dev
`DJANGO_SECRET_KEY` is already generated in `.env`; production uses its own.

### Database

PostgreSQL must be running and the database created before `migrate`:

```bash
sudo service postgresql start          # WSL: no systemd
sudo -u postgres createuser -s "$USER" # once, if your role doesn't exist
createdb gts_neuro
```

Then point `DATABASE_URL` in `.env` at it and apply migrations:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
```

## Running

```bash
.venv/bin/python manage.py runserver    # http://127.0.0.1:8000
```

- `GET /api/health/` — liveness plus a database connection check
- `/admin/` — Django admin (superuser password login; unrelated to Clerk)

Settings default to `config.settings.dev`. Production sets
`DJANGO_SETTINGS_MODULE=config.settings.prod`.

## Authentication

The frontend sends the Clerk session token as `Authorization: Bearer <jwt>`.
`users.authentication.ClerkAuthentication` verifies it against Clerk's JWKS and
resolves the local `User` row by `clerk_user_id`.

Two things to finish on the Clerk side:

1. Add `email` (and ideally `name`, `image_url`) to the session token via
   Clerk's JWT template, so a user hitting the API for the first time can be
   provisioned locally.
2. Add a Clerk webhook syncing `user.created` / `user.updated` / `user.deleted`.
   That is the durable sync path; the lazy creation in the auth class is a
   stopgap.

DRF defaults to `IsAuthenticated`, so new views are private unless they opt out
with `AllowAny` (public catalog, preview lessons, blog).
