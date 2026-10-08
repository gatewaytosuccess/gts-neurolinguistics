# API (Django)

JSON API for the neurolinguistics course platform. The Next.js app in `../web`
is the only client; Django serves no templates apart from the admin.

## Stack

- Django 5.2 + Django REST Framework
- PostgreSQL (local for dev, Amazon RDS in production)
- Clerk for authentication — Django verifies Clerk session JWTs, it does not
  own passwords
- Amazon S3 for lesson media and thumbnails, with CloudFront serving thumbnails
- Stripe Checkout for payments

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
  commerce/          Cart, CartItem, Order, OrderItem, Coupon, the Stripe API module, Stripe webhook
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
- `POST /api/webhooks/stripe/` — Stripe events, signed with `STRIPE_WEBHOOK_SECRET`. Answers 503
  with no secret configured and 400 for a missing or invalid signature or a malformed body; every
  event type is acknowledged with `{"status": "ignored"}` for now
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
- `GET`, `PATCH /api/admin/lessons/<id>/` — a lesson's title, body, preview flag, duration and
  files, with its module and course; `video_url` and `slides_url` are presigned GETs that expire
  after an hour; admins only
- `POST /api/admin/lessons/<id>/uploads/` — a presigned POST for a new `video` (MP4, up to 2 GB)
  or `slides` (PDF, up to 100 MB), by `kind`; `PATCH` its `video_key` or `slides_key` onto the
  lesson to save it, or a blank key to remove it; admins only
- `GET /api/learn/<slug>/` — a course's outline for the lesson viewer: every module and lesson in
  order, each lesson `locked` or not and `completed` or not, the caller's `access` and their
  completed and total lesson counts; signing in is optional. Only an enrolled caller sees anything
  completed, and a visitor gets 404 for a draft course
- `GET /api/learn/<slug>/lessons/<id>/` — a lesson for the lesson viewer, with presigned URLs that
  expire after four hours, the previous and next lesson ids, the caller's `access`
  (`enrolled`, `admin` or `visitor`) and, only when enrolled, their `progress` (`status` and
  `last_position_seconds`); signing in is optional. A locked lesson answers 403 with
  `code: "lesson_locked"`, and a visitor gets 404 for any lesson of a draft course
- `PUT /api/lessons/<id>/progress/` — `{opened?: true, completed?: bool, position_seconds?: int}`
  records the caller opening a lesson, marking it complete or not, or where they are in its video,
  and answers with its `status`, `completed_at`, `last_position_seconds` and the course's
  `lesson_count` and `completed_lesson_count`. Neither `opened` nor `position_seconds` undoes
  completion, and `completed: false` puts the lesson back to `in_progress`. 403 without an active
  enrollment in the lesson's course, admins included
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
rules on deleted and suspended accounts.

DRF defaults to `IsAuthenticated`, so new views are private unless they opt out
with `AllowAny` (public catalog, preview lessons, blog).

## Stripe

Dev uses Stripe's test mode. Every call to the Stripe API goes through
`commerce/stripe_api.py`; tests replace its functions and never reach Stripe.

1. In the Stripe dashboard, with test mode on, copy the secret key
   (`sk_test_...`) from *Developers → API keys* into `STRIPE_SECRET_KEY`.
2. Under *Settings → Payment methods*, leave only Cards and the wallets (Apple
   Pay, Google Pay) on. Checkout offers whatever is enabled there, and a delayed
   method such as a bank debit completes a session before it is paid.
3. Install the [Stripe CLI](https://docs.stripe.com/stripe-cli), run
   `stripe login` once, then forward events to the local API:

   ```bash
   stripe listen \
     --events checkout.session.completed,checkout.session.expired,charge.refunded,charge.dispute.created \
     --forward-to localhost:8000/api/webhooks/stripe/
   ```

   The CLI requires `--events`. Keep the list in step with the event types the
   webhook handles.

   It prints a `whsec_...` signing secret: put it in `STRIPE_WEBHOOK_SECRET` and
   restart `runserver`. The secret stays the same across `stripe listen` runs on
   the same machine.
4. With the forwarder and `runserver` both running, send a test event:

   ```bash
   stripe trigger checkout.session.completed
   ```

   `runserver` logs `POST /api/webhooks/stripe/` with a 200 for each event, and
   the forwarder shows `[200]` next to it.

Both keys are server-only and belong in `api/.env`; the Next.js app never talks
to Stripe directly.
