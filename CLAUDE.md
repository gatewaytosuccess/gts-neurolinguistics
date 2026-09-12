# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a fullstack web application. It's purpose is to serve as a learning platform for neurolinguistics through online courses, as well as to market and sell these courses. There's two main views - a user view (users can signup, buy courses, view courses, progress through owned courses, etc...) and an admin view (admins can upload/edit/delete courses).

## Tech Stack

**Backend**: Python + Django\
**Frontend**: Typescript + Next.js\
**Database**: PostgreSQL on Amazon RDS\
**Object storage**: Amazon S3\
**Auth**: Clerk

## Backend (`api/`)

Django project with a virtualenv at `api/.venv` (gitignored). Run commands as
`.venv/bin/python manage.py <cmd>` from `api/`. Settings are split under
`config/settings/` and default to `config.settings.dev`; configuration is read
from `api/.env` (see `api/.env.example`). Apps: `common`, `users`, `courses`,
`enrollments`, `commerce`, `reviews`. See `api/README.md` for setup details.

## Database Schema

See `SCHEMA.md` at the root of the project.

## Other Files

`SPEC.md` - a high level spec of the project. Free to change if a better alternative to anything in the spec exists.\
`DESIGN.md` - a design for the frontend visuals.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on `gatewaytosuccess/gts-neurolinguistics`, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, using their default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
