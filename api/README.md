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
  users/             custom User model, Clerk JWT authentication, Clerk webhook
  courses/           Course -> Module -> Lesson
  enrollments/       Enrollment, LessonProgress
  commerce/          Cart, CartItem, Order, OrderItem, Coupon
  reviews/           Review
  .venv/             virtualenv (gitignored)
  .env               local secrets (gitignored) — see .env.example
```

Models follow `../SCHEMA.md`. Beyond the health check, the only routes so far
are the ones sign-up needs: `/api/users/me/` and the Clerk webhook.

## Setup

The virtualenv already exists at `api/.venv`. To recreate it:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
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
- `GET /api/users/me/` — the signed-in user's account row
- `POST /api/webhooks/clerk/` — Clerk `user.*` events, Svix-signed
- `/admin/` — Django admin (superuser password login; unrelated to Clerk)

## Tests

```bash
.venv/bin/python -m pytest
```

pytest-django builds a throwaway database, so the role in `DATABASE_URL` needs
`CREATEDB`:

```bash
sudo -u postgres psql -c 'ALTER ROLE myuser CREATEDB;'
```

Settings default to `config.settings.dev`. Production sets
`DJANGO_SETTINGS_MODULE=config.settings.prod`.

## Authentication

The frontend sends the Clerk session token as `Authorization: Bearer <jwt>`.
`users.authentication.ClerkAuthentication` verifies it against Clerk's JWKS and
resolves the local `User` row by `clerk_user_id`.

Local `users` rows are written from two places, both of which copy *from*
Clerk and both of which go through `users.sync` so they cannot disagree:

1. **`POST /api/webhooks/clerk/`** — the durable path. Subscribe the endpoint to
   `user.created`, `user.updated` and `user.deleted` in the Clerk dashboard and
   put its signing secret in `CLERK_WEBHOOK_SIGNING_SECRET`. Webhooks cannot
   reach `localhost`, so test it with the dashboard's test-send or an ngrok
   tunnel.
2. **Just-in-time provisioning** in `ClerkAuthentication` — covers the seconds
   between Clerk redirecting a brand-new user into the app and the
   `user.created` delivery landing. It needs `email` (and ideally `name`,
   `image_url`) in the token claims: add them under *Configure → Sessions →
   Customize session token*, **not** a named JWT template, since `getToken()`
   without a template argument returns the default session token.

The table is a read-only mirror — see `../docs/adr/0001-clerk-owns-identity.md`
for why there is no endpoint to edit a profile, and `users/sync.py` for the
rules on deleted, suspended and banned accounts.

DRF defaults to `IsAuthenticated`, so new views are private unless they opt out
with `AllowAny` (public catalog, preview lessons, blog).
