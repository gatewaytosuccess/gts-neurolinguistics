# API (Django)

JSON API for the neurolinguistics course platform. The Next.js app in `../web`
is the only client; Django serves no templates apart from the admin.

## Stack

- Django 5.2 + Django REST Framework
- PostgreSQL (local for dev, Amazon RDS in production)
- Clerk for authentication — Django verifies Clerk session JWTs, it does not
  own passwords
- Amazon S3 for lesson media and thumbnails, with CloudFront serving thumbnails

## Layout

```
api/
  config/            project config
    settings/
      base.py        shared settings, read from the environment
      dev.py         local development (DEBUG, browsable API, console email)
      prod.py        RDS + TLS + security headers
    urls.py          / admin/ and /api/
  common/            UUID + timestamp base models, /api/health/, the S3 storage module
  users/             custom User model, Clerk JWT authentication, Clerk webhook, IsAdmin
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

To fill the catalog with sample data (dev only, safe to re-run):

```bash
.venv/bin/python manage.py seed_courses
```

It seeds three published courses and one draft, learners at
`seed-learner-N@example.com`, and reviews (one of them hidden). It creates no
enrollments: grant those in Django admin.

## Running

```bash
.venv/bin/python manage.py runserver    # http://127.0.0.1:8000
```

- `GET /api/health/` — liveness plus a database connection check
- `GET /api/users/me/` — the signed-in user's account row
- `POST /api/webhooks/clerk/` — Clerk `user.*` events, Svix-signed
- `GET /api/admin/courses/` — every course, drafts included; admins only
- `POST /api/admin/courses/` — create a draft course; admins only
- `GET`, `PATCH`, `DELETE /api/admin/courses/<id>/` — a course's details; `DELETE` answers 409 for
  a course anyone has enrolled in, bought or reviewed; admins only
- `POST /api/admin/courses/<id>/publish/`, `POST /api/admin/courses/<id>/unpublish/` — publish answers
  400 with `{"problems": [...]}` when the course can't be published; admins only
- `POST /api/admin/courses/<id>/thumbnail/upload/` — a presigned POST for a new thumbnail
  (JPEG, PNG or WebP, up to 5 MB); `PATCH` its `thumbnail_key` onto the course to save it,
  or a blank key to remove it; admins only
- `GET /api/admin/courses/<id>/curriculum/` — modules and lessons in order, with progress counts; admins only
- `POST /api/admin/courses/<id>/modules/`, `PATCH`, `DELETE /api/admin/modules/<id>/`,
  `POST /api/admin/modules/<id>/move/` — add, rename, delete and reorder modules; admins only
- `POST /api/admin/modules/<id>/lessons/`, `DELETE /api/admin/lessons/<id>/`,
  `POST /api/admin/lessons/<id>/move/` — add, delete and reorder lessons, across modules too; admins only
- `GET`, `PATCH /api/admin/lessons/<id>/` — a lesson's title, body, preview flag and duration,
  with its module and course; admins only
- `/admin/` — Django admin (superuser password login; unrelated to Clerk)

Any admin write to a published course, its curriculum or its lessons that would leave it
unpublishable is rolled back and answers 400 with `{"problems": [...]}`.

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
   put its signing secret in `CLERK_WEBHOOK_SIGNING_SECRET`.

   **Not configured yet** (issue #2): Clerk cannot reach `localhost`, so this
   waits until the API has a public host. With the secret unset the endpoint
   answers 503 rather than trusting an unverified payload, and account changes
   made in Clerk — a deletion, an email change — do not reach the mirror. Sign-up
   itself is unaffected, because provisioning falls through to (2). To exercise
   it locally anyway, put a tunnel (`cloudflared tunnel --url http://localhost:8000`)
   in front and point the dashboard endpoint at that.
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
