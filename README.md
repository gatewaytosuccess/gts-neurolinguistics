## Prerequisites

- Python 3.13
- PostgreSQL 18+
- Node.js 20.9+ (npm)
- A Clerk application (for anything beyond the health check)

## Backend dev setup

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

### 4. Storage (S3 and CloudFront)

Needed for uploads: thumbnails now, lesson video and slides next. Dev uses
real buckets of its own, never production's. Do this in the AWS console, all
in one region.

**Buckets.** Create two buckets, such as `gts-neuro-dev-private` (lesson
video and slides) and `gts-neuro-dev-thumbnails`. Leave *Block all public
access* on and ACLs disabled on both.

**CORS.** The browser uploads straight to S3, so on each bucket, under
*Permissions → Cross-origin resource sharing*:

```json
[
  {
    "AllowedOrigins": ["http://localhost:3000"],
    "AllowedMethods": ["POST"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3000
  }
]
```

**CloudFront.** Create a distribution whose origin is the thumbnail bucket
(the bucket itself, not a website endpoint). Under *Origin access*, choose
*Origin access control settings* and create a control that signs requests.
Redirect HTTP to HTTPS, and keep the default *CachingOptimized* policy.

**Thumbnail bucket policy.** Only that distribution may read the bucket.
CloudFront offers this policy after creating the distribution; under the
bucket's *Permissions → Bucket policy* it reads:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::gts-neuro-dev-thumbnails/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::<account-id>:distribution/<distribution-id>"
        }
      }
    }
  ]
}
```

The private bucket gets no policy: only presigned URLs reach it.

**IAM user.** Create a user with no console access, and give it an inline
policy limited to the two buckets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": [
        "arn:aws:s3:::gts-neuro-dev-private/*",
        "arn:aws:s3:::gts-neuro-dev-thumbnails/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": [
        "arn:aws:s3:::gts-neuro-dev-private",
        "arn:aws:s3:::gts-neuro-dev-thumbnails"
      ]
    }
  ]
}
```

`s3:ListBucket` makes S3 answer 404, not 403, for a missing object, which is
how the API tells an unfinished upload from a permissions problem. Create an
access key for the user (*Application running outside AWS*).

**`.env`.** Fill in `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_PRIVATE_BUCKET_NAME`,
`AWS_THUMBNAIL_BUCKET_NAME`, and `CLOUDFRONT_DOMAIN` (the distribution's
domain, such as `d1234abcd.cloudfront.net`, with no `https://`).

To check it, upload a thumbnail on a draft course at
`/admin/courses/<id>`: it should appear on the page.

### 5. Run

```bash
.venv/bin/python manage.py runserver    # http://127.0.0.1:8000
```

- `GET /api/health/` — liveness plus a database connection check
- `/admin/` — Django admin (superuser password login, unrelated to Clerk)

Settings default to `config.settings.dev`; production sets
`DJANGO_SETTINGS_MODULE=config.settings.prod`.

## Frontend dev setup

All frontend commands run from `web/`. The backend must be running first.

### 1. Dependencies

```bash
cd web
npm install
```

### 2. Environment

```bash
cp .env.local.example .env.local
```

Fill in `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` from the
Clerk dashboard (API keys). Use the same Clerk application as `api/.env`, or
Django will reject the session tokens the frontend sends.

`API_BASE_URL` defaults to `http://127.0.0.1:8000`. It is server-only: the
browser never calls Django directly.

### 3. Run

```bash
npm run dev                             # http://localhost:3000
```

Keep it on port 3000 — the CORS, CSRF, and Clerk authorized-party settings in
`api/.env` expect that origin.

Other scripts: `npm run build`, `npm run start`, `npm run lint`. See
`web/README.md` for layout and conventions.

## Repo layout

```
api/            Django project (config, common, users, courses,
                enrollments, commerce, reviews)
web/            Next.js app (App Router, Tailwind v4, Clerk)
SPEC.md         feature spec, grouped by page
SCHEMA.md       database schema
DESIGN.md       frontend design
```
